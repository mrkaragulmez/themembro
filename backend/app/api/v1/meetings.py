# backend/app/api/v1/meetings.py
# Faz 4 — WebRTC Sesli Toplantı API endpoint'leri
#
# POST /api/v1/meetings/              → Toplantı oluştur, LiveKit token döndür
# GET  /api/v1/meetings/              → Tenant toplantılarını listele
# POST /api/v1/meetings/{id}/end      → Toplantıyı sonlandır
# GET  /api/v1/meetings/{id}/transcripts → Transcript satırlarını listele
# POST /api/v1/meetings/{id}/transcripts → Voice Worker → transcript satırı ekle

from __future__ import annotations

import json
import uuid
import structlog

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Meeting, MeetingTranscript, Membro
from app.core.config import settings

log = structlog.get_logger()

router = APIRouter(prefix="/meetings", tags=["meetings"])


# ─── Pydantic Şemaları ───────────────────────────────────────────────────────

class MeetingCreateRequest(BaseModel):
    membro_id: str  # Toplantıya katılacak Membro'nun ID'si


class MeetingCreateResponse(BaseModel):
    meeting_id:  str
    room_name:   str
    livekit_url: str
    token:       str   # LiveKit Access Token (JWT)
    status:      str = "active"


class MeetingResponse(BaseModel):
    id:          str
    membro_id:   str | None
    room_name:   str
    status:      str
    summary:     str | None
    started_at:  str
    ended_at:    str | None


class TranscriptAddRequest(BaseModel):
    speaker: str   # "user" veya membro_id
    text:    str


class TranscriptResponse(BaseModel):
    id:          str
    meeting_id:  str
    speaker:     str
    text:        str
    created_at:  str


# ─── Yardımcı: LiveKit token üretimi ─────────────────────────────────────────

def _build_livekit_token(room_name: str, identity: str, display_name: str) -> str:
    """LiveKit Access Token (JWT) oluşturur.

    livekit-api paketi token üretimini sağlar.
    Paket mevcut değilse (geliştirme/test ortamı) dummy token döner.
    """
    try:
        from livekit.api import AccessToken, VideoGrants  # type: ignore

        grants = VideoGrants(room_join=True, room=room_name)
        token = (
            AccessToken(
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
            )
            .with_identity(identity)
            .with_name(display_name)
            .with_grants(grants)
        )
        return token.to_jwt()
    except ImportError:
        # livekit-api henüz kurulu değilse test placeholder token
        log.warning("livekit_api_not_installed_using_dummy_token")
        import base64, json as _json
        payload = {"room": room_name, "identity": identity, "dummy": True}
        return base64.urlsafe_b64encode(_json.dumps(payload).encode()).decode()


async def _dispatch_voice_worker(room_name: str, tenant_id: str, membro_id: str) -> None:
    """LiveKit Agents dispatch API'sini kullanarak Voice Worker job'ı tetikler.

    Worker, LiveKit Server'dan bu odaya ajan olarak katılma talebi alır.
    """
    try:
        from livekit.api import LiveKitAPI  # type: ignore
        from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest  # type: ignore

        metadata = json.dumps({"tenant_id": tenant_id, "membro_id": membro_id})
        async with LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        ) as lk:
            await lk.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(
                    room_name=room_name,
                    agent_name="membro-voice-agent",  # worker.py'de kayıtlı isim
                    metadata=metadata,
                )
            )
        log.info("voice_worker_dispatched", room=room_name, membro=membro_id)
    except Exception as exc:
        # Worker dispatch başarısız olsa da toplantı oluşturulmuş olsun;
        # kullanıcı token'ı alır, worker manuel tetiklenebilir.
        log.warning("voice_worker_dispatch_failed", error=str(exc), room=room_name)


# ─── POST /meetings/ ─────────────────────────────────────────────────────────

@router.post("/", response_model=MeetingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    body:    MeetingCreateRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    """Sesli toplantı başlatır.

    1. LiveKit room adı üretir (tenant+membro+uuid).
    2. PostgreSQL'e MO_Meetings kaydı oluşturur.
    3. LiveKit Access Token (JWT) üretir → browser'ın Room'a bağlanması için.
    4. Voice Worker job'ını dispatch eder → Membro Room'a ajan olarak katılır.
    """
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    user_id:   str | None = getattr(request.state, "user_id", None)

    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

    # Membro varlık kontrolü (tenant izolasyonu)
    try:
        membro_uuid = uuid.UUID(body.membro_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Geçersiz membro_id formatı")

    result = await db.execute(
        select(Membro).where(
            Membro.id == membro_uuid,
            Membro.tenant_id == uuid.UUID(tenant_id),
            Membro.is_active == True,
        )
    )
    membro = result.scalars().first()
    if not membro:
        raise HTTPException(status_code=404, detail="Membro bulunamadı")

    # Odaya özgü benzersiz isim
    room_name = f"{tenant_id[:8]}_{body.membro_id[:8]}_{uuid.uuid4().hex[:8]}"

    meeting = Meeting(
        tenant_id=uuid.UUID(tenant_id),
        membro_id=membro_uuid,
        room_name=room_name,
        started_by=uuid.UUID(user_id) if user_id else None,
        status="active",
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    # Kullanıcı için LiveKit access token
    identity     = user_id or "anonymous"
    display_name = str(user_id)[:8] if user_id else "Misafir"
    token = _build_livekit_token(room_name, identity, display_name)

    # Ajan dispatch (hata toleranslı)
    await _dispatch_voice_worker(room_name, tenant_id, body.membro_id)

    log.info("meeting_created", meeting_id=str(meeting.id), room=room_name, tenant=tenant_id)

    return MeetingCreateResponse(
        meeting_id=str(meeting.id),
        room_name=room_name,
        livekit_url=settings.livekit_url,
        token=token,
        status="active",
    )


# ─── GET /meetings/ ──────────────────────────────────────────────────────────

@router.get("/", response_model=list[MeetingResponse])
async def list_meetings(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    """Tenant'ın tüm toplantılarını döndürür (en yeni önce)."""
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

    result = await db.execute(
        select(Meeting)
        .where(Meeting.tenant_id == uuid.UUID(tenant_id))
        .order_by(Meeting.started_at.desc())
    )
    meetings = result.scalars().all()

    return [
        MeetingResponse(
            id=str(m.id),
            membro_id=str(m.membro_id) if m.membro_id else None,
            room_name=m.room_name,
            status=m.status,
            summary=m.summary,
            started_at=m.started_at.isoformat(),
            ended_at=m.ended_at.isoformat() if m.ended_at else None,
        )
        for m in meetings
    ]


# ─── POST /meetings/{meeting_id}/end ─────────────────────────────────────────

@router.post("/{meeting_id}/end", response_model=MeetingResponse)
async def end_meeting(
    meeting_id: str,
    request:    Request,
    db:         AsyncSession = Depends(get_db),
):
    """Toplantıyı sonlandırır; status → 'ended', ended_at güncellenir."""
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

    result = await db.execute(
        select(Meeting).where(
            Meeting.id == uuid.UUID(meeting_id),
            Meeting.tenant_id == uuid.UUID(tenant_id),
        )
    )
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Toplantı bulunamadı")

    if meeting.status == "ended":
        raise HTTPException(status_code=409, detail="Toplantı zaten sonlandırılmış")

    meeting.status   = "ended"
    meeting.ended_at = datetime.utcnow()
    await db.commit()
    await db.refresh(meeting)

    log.info("meeting_ended", meeting_id=meeting_id, tenant=tenant_id)

    return MeetingResponse(
        id=str(meeting.id),
        membro_id=str(meeting.membro_id) if meeting.membro_id else None,
        room_name=meeting.room_name,
        status=meeting.status,
        summary=meeting.summary,
        started_at=meeting.started_at.isoformat(),
        ended_at=meeting.ended_at.isoformat() if meeting.ended_at else None,
    )


# ─── GET /meetings/{meeting_id}/transcripts ──────────────────────────────────

@router.get("/{meeting_id}/transcripts", response_model=list[TranscriptResponse])
async def get_transcripts(
    meeting_id: str,
    request:    Request,
    db:         AsyncSession = Depends(get_db),
):
    """Bir toplantının tüm transcript satırlarını döndürür (kronolojik)."""
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

    # Toplantı varlık + tenant kontrolü
    meet_result = await db.execute(
        select(Meeting).where(
            Meeting.id == uuid.UUID(meeting_id),
            Meeting.tenant_id == uuid.UUID(tenant_id),
        )
    )
    if not meet_result.scalars().first():
        raise HTTPException(status_code=404, detail="Toplantı bulunamadı")

    result = await db.execute(
        select(MeetingTranscript)
        .where(
            MeetingTranscript.meeting_id == uuid.UUID(meeting_id),
            MeetingTranscript.tenant_id  == uuid.UUID(tenant_id),
        )
        .order_by(MeetingTranscript.created_at.asc())
    )
    rows = result.scalars().all()

    return [
        TranscriptResponse(
            id=str(r.id),
            meeting_id=str(r.meeting_id),
            speaker=r.speaker,
            text=r.text,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


# ─── POST /meetings/{meeting_id}/transcripts ─────────────────────────────────

@router.post("/{meeting_id}/transcripts", response_model=TranscriptResponse, status_code=status.HTTP_201_CREATED)
async def add_transcript(
    meeting_id: str,
    body:       TranscriptAddRequest,
    request:    Request,
    db:         AsyncSession = Depends(get_db),
):
    """Voice Worker'dan gelen transcript satırını veritabanına yazar.

    Speaker alanı "user" (kullanıcı) ya da membro_id (ajan) olabilir.
    """
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

    meet_result = await db.execute(
        select(Meeting).where(
            Meeting.id == uuid.UUID(meeting_id),
            Meeting.tenant_id == uuid.UUID(tenant_id),
        )
    )
    meeting = meet_result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Toplantı bulunamadı")

    row = MeetingTranscript(
        tenant_id=uuid.UUID(tenant_id),
        meeting_id=uuid.UUID(meeting_id),
        speaker=body.speaker,
        text=body.text,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return TranscriptResponse(
        id=str(row.id),
        meeting_id=str(row.meeting_id),
        speaker=row.speaker,
        text=row.text,
        created_at=row.created_at.isoformat(),
    )
