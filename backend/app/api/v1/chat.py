# backend/app/api/v1/chat.py
# Faz 2 — Ajan Chat Endpoint'leri
# Faz 2 güncel: Graf artık app.state.graph üzerinden erişilir;
# startup'ta PostgreSQL checkpointer ile derlendiğinden burada derleme yok.
#
# POST /api/v1/agents/{membro_id}/chat      → tek yanıt (JSON)
# POST /api/v1/agents/{membro_id}/chat/stream → SSE akışı

from __future__ import annotations

import json
import uuid
import structlog

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.state import MembroState
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
):
    """Membro ajanına tek mesaj gönderir, tam yanıt döner."""
    # Tenant kimliği middleware tarafından request.state'e yazılır
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id bulunamadı")

    # Graf startup'ında PG checkpointer ile derlendi (bkz. main.py lifespan)
    graph = request.app.state.graph

    conversation_id = body.conversation_id or str(uuid.uuid4())

    initial_state = MembroState(
        messages=[HumanMessage(content=body.message)],
        tenant_id=tenant_id,
        membro_id=membro_id,
        conversation_id=conversation_id,
    )

    config = {"configurable": {"thread_id": conversation_id}}

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

    return ChatResponse(
        conversation_id=conversation_id,
        reply=reply_text,
        agent_used=next_agent,
        turn_count=turn_count,
    )


# ─── POST /agents/{membro_id}/chat/stream ───────────────────────────────────

@router.post("/{membro_id}/chat/stream")
async def chat_stream(
    membro_id: str,
    body: ChatRequest,
    request: Request,
):
    """Membro ajanına mesaj gönderir, SSE akışı ile token-token yanıt döner."""
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

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
        try:
            async for chunk in graph.astream(initial_state, config=config):
                # chunk: {node_name: state_update}
                for node_name, update in chunk.items():
                    if isinstance(update, dict) and "messages" in update:
                        for msg in update["messages"]:
                            if hasattr(msg, "content"):
                                payload = {
                                    "type": "token",
                                    "node": node_name,
                                    "content": msg.content,
                                }
                                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            log.error("chat_stream.error", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        finally:
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
