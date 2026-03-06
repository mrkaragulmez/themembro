# backend/app/api/v1/chat.py
# Faz 2 — Ajan Chat Endpoint'leri
# Faz 2 güncel: Graf artık app.state.graph üzerinden erişilir;
# startup'ta PostgreSQL checkpointer ile derlendiğinden burada derleme yok.
# Faz 6 güncel: Mesajlar MO_Conversations + MO_Messages tablolarına kalıcı olarak kaydedilir.
#
# POST /api/v1/agents/{membro_id}/chat          → tek yanıt (JSON)
# POST /api/v1/agents/{membro_id}/chat/stream   → SSE akışı
# GET  /api/v1/agents/{membro_id}/history       → geçmiş mesajlar

from __future__ import annotations

import json
import uuid
import structlog
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import MembroState
from app.db.models import Conversation, Message
from app.db.session import get_db, get_db_session
from langchain_core.messages import HumanMessage

log = structlog.get_logger()

router = APIRouter(prefix="/agents", tags=["agents"])

# ─── Şemalar ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None  # None ise yeni konuşma başlatılır


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    agent_used: str | None = None
    turn_count: int



# ─── POST /agents/{membro_id}/chat ──────────────────────────────────────────

@router.post("/{membro_id}/chat", response_model=ChatResponse)
async def chat(
    membro_id: str,
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Membro ajanına tek mesaj gönderir, tam yanıt döner."""
    # Tenant kimliği middleware tarafından request.state'e yazılır
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id bulunamadı")

    # Graf startup'ında PG checkpointer ile derlendi (bkz. main.py lifespan)
    graph = request.app.state.graph

    # Faz 5: Input uzunluk limiti — prompt injection yüzey azaltma
    from app.core.config import settings as _s
    message_text = body.message[: _s.input_max_length]

    conversation_id = body.conversation_id or str(uuid.uuid4())

    initial_state = MembroState(
        messages=[HumanMessage(content=message_text)],
        tenant_id=tenant_id,
        membro_id=membro_id,
        conversation_id=conversation_id,
    )

    config = {
        "configurable": {"thread_id": conversation_id},
        # Faz 5: LangSmith trace metadata — tenant + membro bazlı izleme
        "metadata": {
            "tenant_id":    tenant_id,
            "membro_id":    membro_id,
            "session_type": "chat",
        },
    }

    log.info(
        "chat.invoke",
        tenant_id=tenant_id,
        membro_id=membro_id,
        conversation_id=conversation_id,
    )

    try:
        result: MembroState = await graph.ainvoke(initial_state, config=config)  # type: ignore
    except Exception as exc:
        log.error("chat.invoke_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Ajan hatası: {exc}") from exc

    # Son mesaj yanıt — ainvoke AddableValuesDict döndürür, dict erişimi gerekir
    messages = result["messages"] if isinstance(result, dict) else result.messages
    reply_msgs = [m for m in messages if m.type == "ai"]
    reply_text = reply_msgs[-1].content if reply_msgs else "(yanıt üretilemedi)"

    next_agent = result.get("next_agent") if isinstance(result, dict) else result.next_agent
    turn_count = (result.get("turn_count") or 0) if isinstance(result, dict) else result.turn_count

    # Mesajları veritabanına kaydet
    user_id: str | None = getattr(request.state, "user_id", None)
    await _persist_messages(db, tenant_id, membro_id, user_id or "", conversation_id, message_text, reply_text)

    return ChatResponse(
        conversation_id=conversation_id,
        reply=reply_text,
        agent_used=next_agent,
        turn_count=turn_count,
    )


# ─── Yardımcı: konuşma + mesajları kaydet ────────────────────────────────────

async def _persist_messages(
    db: AsyncSession,
    tenant_id: str,
    membro_id: str,
    user_id: str,
    conversation_id: str,
    user_content: str,
    assistant_content: str,
) -> None:
    """MO_Conversations (upsert) + MO_Messages (user + assistant) kaydeder."""
    try:
        tid = uuid.UUID(tenant_id)
        cid = uuid.UUID(conversation_id)
        mid = uuid.UUID(membro_id)
        uid = uuid.UUID(user_id) if user_id else None

        # user_id zorunlu — yoksa persist etme
        if uid is None:
            log.warning("chat.db_persist_skip", reason="user_id yok")
            return

        # Konuşma bul ya da oluştur
        result = await db.execute(select(Conversation).where(Conversation.id == cid))
        conv = result.scalar_one_or_none()
        if conv is None:
            conv = Conversation(
                id=cid,
                tenant_id=tid,
                membro_id=mid,
                user_id=uid,
                title=user_content[:80],  # ilk mesajdan kısa başlık
            )
            db.add(conv)
            await db.flush()

        # Kullanıcı mesajı — önce flush et ki created_at asistandan küçük olsun
        now = datetime.now(timezone.utc)
        db.add(Message(
            tenant_id=tid,
            conversation_id=cid,
            role="user",
            content=user_content,
            metadata_json={},
            created_at=now,
        ))
        await db.flush()

        # Asistan yanıtı — 1ms sonra ki sıralama garantili olsun
        if assistant_content:
            db.add(Message(
                tenant_id=tid,
                conversation_id=cid,
                role="assistant",
                content=assistant_content,
                metadata_json={},
                created_at=now + timedelta(milliseconds=1),
            ))

        await db.commit()
    except Exception as exc:
        log.error("chat.db_persist_error", error=str(exc))
        await db.rollback()


# ─── POST /agents/{membro_id}/chat/stream ───────────────────────────────────

@router.post("/{membro_id}/chat/stream")
async def chat_stream(
    membro_id: str,
    body: ChatRequest,
    request: Request,
):
    """Membro ajanına mesaj gönderir, SSE akışı ile token-token yanıt döner.

    NOT: Bağımlılık enjeksiyonu (Depends(get_db)) StreamingResponse generator'ından
    önce kapandığından, mesaj kalıcılığı için generator içinde taze session açılır.
    """
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")
    user_id: str | None = getattr(request.state, "user_id", None)

    conversation_id = body.conversation_id or str(uuid.uuid4())

    initial_state = MembroState(
        messages=[HumanMessage(content=body.message)],
        tenant_id=tenant_id,
        membro_id=membro_id,
        conversation_id=conversation_id,
    )

    config = {"configurable": {"thread_id": conversation_id}}

    # Graf startup'ında PG checkpointer ile derlendi (bkz. main.py lifespan)
    graph = request.app.state.graph

    async def event_generator():
        # Konuşma başlangıç metaverisi
        yield f"data: {json.dumps({'conversation_id': conversation_id, 'type': 'start'})}\n\n"
        reply_content = ""
        try:
            async for chunk in graph.astream(initial_state, config=config):
                # chunk: {node_name: state_update}
                for node_name, update in chunk.items():
                    if isinstance(update, dict) and "messages" in update:
                        for msg in update["messages"]:
                            if hasattr(msg, "content"):
                                token = msg.content
                                reply_content += token
                                payload = {
                                    "type": "token",
                                    "node": node_name,
                                    "content": token,
                                }
                                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            log.error("chat_stream.error", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        finally:
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            # Streaming bitince RLS bağlamı olan taze session ile mesajları kaydet
            # (Depends(get_db) generator öncesi kapandığından get_db_session kullanılır)
            async with get_db_session(tenant_id=tenant_id) as fresh_db:
                await _persist_messages(
                    fresh_db, tenant_id, membro_id, user_id or "", conversation_id, body.message, reply_content
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── GET /agents/{membro_id}/history ─────────────────────────────────────────

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    membro_id: str
    conversation_id: str


@router.get("/{membro_id}/history", response_model=list[MessageOut])
async def get_history(
    membro_id: str,
    request: Request,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Membro'ya ait son mesajları döner (user + assistant, tarihe göre sıralı)."""
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

    try:
        mid = uuid.UUID(membro_id)
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz UUID")

    # Konuşmaları bul → mesajları çek
    stmt = (
        select(Message, Conversation.membro_id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.membro_id == mid,
            Conversation.tenant_id == tid,
            Message.tenant_id == tid,
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Eski → yeni sıralama (desc ile aldık, tersini döndür)
    rows = list(reversed(rows))

    return [
        MessageOut(
            id=str(row.Message.id),
            role=row.Message.role,
            content=row.Message.content,
            created_at=row.Message.created_at.isoformat(),
            membro_id=str(row.membro_id),
            conversation_id=str(row.Message.conversation_id),
        )
        for row in rows
    ]
