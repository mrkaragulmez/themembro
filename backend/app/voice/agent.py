# backend/app/voice/agent.py
# Faz 4 — Membro Voice Agent
#
# LiveKit Room'a tam katılımcı olarak dahil olan WebRTC ses ajanı.
# OpenAI Realtime API (native audio) ile STT+TTS zincirsiz ~300ms gecikme sağlar.
# Transcript satırları doğrudan PostgreSQL'e yazılır.

from __future__ import annotations

import asyncio
import json
import structlog
import uuid
from datetime import datetime

log = structlog.get_logger()


# ─── Membro Voice Agent sınıfı ──────────────────────────────────────────────

class MembroVoiceAgent:
    """LiveKit Room'a ajan olarak katılan Membro ses temsilcisi.

    Attributes:
        tenant_id:  İlgili kiracı UUID'si (RLS ve log için).
        membro_id:  Hangi Membro'nun ses ajanı olduğu.
        meeting_id: Açık toplantı kaydının UUID'si (transcript için).
        session:    LiveKit AgentSession (başlatılırken atanır).
    """

    def __init__(self, tenant_id: str, membro_id: str, meeting_id: str | None = None):
        self.tenant_id  = tenant_id
        self.membro_id  = membro_id
        self.meeting_id = meeting_id
        self.session    = None  # entrypoint'te atanır

    # ─── Yaşam döngüsü kancaları ────────────────────────────────

    async def on_enter(self) -> None:
        """Kullanıcı Room'a katıldığında karşılama mesajı gönderir."""
        if self.session:
            await self.session.say(
                "Merhaba! Ben Membro'yum. Size nasıl yardımcı olabilirim?",
                allow_interruptions=True,
            )

    # ─── Transcript yazma ───────────────────────────────────────

    async def write_transcript(self, speaker: str, text: str) -> None:
        """Bir transcript satırını PostgreSQL'e yazar.

        Hata toleranslıdır — transcript yazma başarısız olsa da toplantı sürer.
        """
        if not self.meeting_id or not text.strip():
            return
        try:
            import asyncpg  # type: ignore
            from app.core.config import settings

            # asyncpg ile doğrudan yazma (FastAPI session'ından bağımsız)
            conn = await asyncpg.connect(
                settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
            )
            try:
                await conn.execute(
                    """
                    INSERT INTO "MO_MeetingTranscripts"
                        (id, tenant_id, meeting_id, speaker, text)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    uuid.uuid4(),
                    uuid.UUID(self.tenant_id),
                    uuid.UUID(self.meeting_id),
                    speaker,
                    text,
                )
            finally:
                await conn.close()
        except Exception as exc:
            log.warning("transcript_write_failed", error=str(exc), speaker=speaker)


# ─── LiveKit entrypoint ──────────────────────────────────────────────────────

async def entrypoint(ctx):  # ctx: livekit.agents.JobContext
    """Her yeni Voice Worker job'u için çağrılır.

    Akış:
    1. Room'a bağlan.
    2. Metadata'dan tenant_id / membro_id / meeting_id oku.
    3. Silero VAD + OpenAI Realtime Model ile AgentSession kur.
    4. Session'ı başlat; ajan Room'a ajan olarak katılır.
    5. Karşılama mesajı gönder.
    """
    await ctx.connect()

    metadata: dict = {}
    try:
        metadata = json.loads(ctx.job.metadata or "{}")
    except json.JSONDecodeError:
        log.warning("voice_worker_invalid_metadata", raw=ctx.job.metadata)

    tenant_id  = metadata.get("tenant_id", "")
    membro_id  = metadata.get("membro_id", "")
    meeting_id = metadata.get("meeting_id")

    log.info(
        "voice_worker_job_started",
        room=ctx.room.name,
        tenant=tenant_id,
        membro=membro_id,
        meeting=meeting_id,
    )

    # ─── Lazy import — livekit paketi yoksa hata net olsun ──────
    try:
        from livekit.agents import AgentSession, RoomInputOptions  # type: ignore
        from livekit.plugins import openai as lk_openai, silero    # type: ignore
    except ImportError as exc:
        log.error("livekit_agents_not_installed", error=str(exc))
        return

    from app.core.config import settings  # circular import önlemi: geç import

    # ─── OpenAI Realtime Model (native audio — STT/TTS pipeline yok) ────────
    # CF AI Gateway WebSocket proxy üzerinden bağlanır:
    # wss://gateway.ai.cloudflare.com/v1/{account}/{gateway}/openai/realtime
    cf_realtime_url = (
        f"wss://gateway.ai.cloudflare.com/v1"
        f"/{settings.cf_account_id}/{settings.cf_gateway_id}/openai/realtime"
    ) if settings.cf_account_id else None  # CF yoksa OpenAI direkt

    realtime_model = lk_openai.realtime.RealtimeModel(
        model="gpt-4o-realtime-preview",
        **({"base_url": cf_realtime_url} if cf_realtime_url else {}),
        api_key=settings.cf_aig_token or None,
        voice="alloy",
        # Server-side VAD parametreleri
        turn_detection=lk_openai.realtime.ServerVadOptions(
            threshold=0.5,
            prefix_padding_ms=300,
            silence_duration_ms=600,
        ),
        instructions=(
            "Sen Membro adlı bir yapay zeka asistanısın. "
            "Türkçe konuşuyorsun. Kısa, net ve samimi yanıtlar ver. "
            "Kullanıcı araya girerse hemen dur."
        ),
    )

    # ─── Silero VAD (client-side, interruption detection için) ──────────────
    vad = silero.VAD.load()

    # ─── AgentSession ────────────────────────────────────────────────────────
    session = AgentSession(
        vad=vad,
        llm=realtime_model,   # Realtime modelde stt/tts ayrıca verilmez
    )

    agent = MembroVoiceAgent(
        tenant_id=tenant_id,
        membro_id=membro_id,
        meeting_id=meeting_id,
    )
    agent.session = session

    # ─── Transcript hook: her konuşma bittiğinde kaydet ─────────────────────
    @session.on("user_speech_committed")
    async def _on_user_speech(event) -> None:  # type: ignore
        await agent.write_transcript("user", getattr(event, "text", ""))

    @session.on("agent_speech_committed")
    async def _on_agent_speech(event) -> None:  # type: ignore
        await agent.write_transcript(membro_id or "membro", getattr(event, "text", ""))

    # ─── Session başlat ──────────────────────────────────────────────────────
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(noise_cancellation=True),
    )

    # Kullanıcı geldiğinde karşılama (Room'a katılır katılmaz)
    await agent.on_enter()
