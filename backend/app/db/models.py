# backend/app/db/models.py
# Faz 1 — SQLAlchemy ORM modelleri (MO_ prefix'li tablolar)
# Her model RLS politikalarıyla korunur; tenant_id her zaman JWT'den gelir

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, String, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ─── MO_Tenants ────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "MO_Tenants"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:       Mapped[str]       = mapped_column(String(255), nullable=False)
    slug:       Mapped[str]       = mapped_column(String(63), nullable=False, unique=True, index=True)
    plan:       Mapped[str]       = mapped_column(String(32), nullable=False, default="starter")
    is_active:  Mapped[bool]      = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users:    Mapped[list["User"]]    = relationship(back_populates="tenant")
    membros:  Mapped[list["Membro"]]  = relationship(back_populates="tenant")


# ─── MO_Users ──────────────────────────────────────────────────

class User(Base):
    __tablename__ = "MO_Users"

    id:             Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email:          Mapped[str]       = mapped_column(String(255), nullable=False)
    password_hash:  Mapped[str]       = mapped_column(Text, nullable=False)
    role:           Mapped[str]       = mapped_column(String(50), nullable=False, default="member")
    full_name:      Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active:      Mapped[bool]      = mapped_column(Boolean, nullable=False, default=True)
    created_at:     Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:     Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant:         Mapped["Tenant"]              = relationship(back_populates="users")
    refresh_tokens: Mapped[list["RefreshToken"]]  = relationship(back_populates="user")


# ─── MO_RefreshTokens ──────────────────────────────────────────

class RefreshToken(Base):
    __tablename__ = "MO_RefreshTokens"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Users.id", ondelete="CASCADE"), nullable=False)
    token_hash:   Mapped[str]       = mapped_column(String(255), nullable=False, unique=True)
    expires_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False)
    revoked:      Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    created_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


# ─── MO_Membros ────────────────────────────────────────────────

class Membro(Base):
    __tablename__ = "MO_Membros"

    id:            Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:     Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name:          Mapped[str]          = mapped_column(String(255), nullable=False)
    description:   Mapped[str | None]   = mapped_column(Text)
    system_prompt: Mapped[str | None]   = mapped_column(Text)
    tools_json:    Mapped[dict | None]  = mapped_column(JSONB, default=list)
    is_active:     Mapped[bool]         = mapped_column(Boolean, nullable=False, default=True)
    created_at:    Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant:        Mapped["Tenant"]            = relationship(back_populates="membros")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="membro")


# ─── MO_Conversations ──────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "MO_Conversations"

    id:         Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:  Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    membro_id:  Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Membros.id", ondelete="SET NULL"), nullable=True)
    user_id:    Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Users.id", ondelete="SET NULL"), nullable=True)
    type:       Mapped[str]         = mapped_column(String(16), nullable=False, default="chat")  # chat | voice
    started_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    membro:   Mapped["Membro"]       = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


# ─── MO_Messages ───────────────────────────────────────────────

class Message(Base):
    __tablename__ = "MO_Messages"

    id:              Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role:            Mapped[str]       = mapped_column(String(16), nullable=False)  # user | assistant | system
    content:         Mapped[str]       = mapped_column(Text, nullable=False)
    tokens_used:     Mapped[int | None] = mapped_column()
    created_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


# ─── MO_KnowledgeDocs ──────────────────────────────────────────

class KnowledgeDoc(Base):
    __tablename__ = "MO_KnowledgeDocs"

    id:         Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:  Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    membro_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Membros.id", ondelete="SET NULL"), nullable=True)
    title:      Mapped[str]         = mapped_column(String(500), nullable=False)
    content:    Mapped[str]         = mapped_column(Text, nullable=False)
    status:     Mapped[str]         = mapped_column(String(32), nullable=False, default="pending")  # pending | processing | indexed | failed
    extra:      Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─── MO_Eventlog ───────────────────────────────────────────────

class Eventlog(Base):
    __tablename__ = "MO_Eventlog"

    id:          Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Users.id", ondelete="SET NULL"), nullable=True)
    service:     Mapped[str]            = mapped_column(String(64), nullable=False)   # api | voice_worker | langgraph | ingestion
    level:       Mapped[str]            = mapped_column(String(16), nullable=False)   # ERROR | WARNING | CRITICAL | INFO
    code:        Mapped[str | None]     = mapped_column(String(64), index=True)
    message:     Mapped[str]            = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None]     = mapped_column(Text)
    request_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    extra:       Mapped[dict | None]    = mapped_column("metadata", JSONB)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# ─── MO_Meetings ───────────────────────────────────────────────
# Faz 4 — LiveKit WebRTC sesli toplantı oturumları

class Meeting(Base):
    __tablename__ = "MO_Meetings"

    id:          Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:   Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    membro_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Membros.id", ondelete="SET NULL"), nullable=True)
    # LiveKit room adı — her toplantıya özgü; format: {tenant_id}_{membro_id}_{uuid}
    room_name:   Mapped[str]          = mapped_column(String(255), nullable=False, unique=True, index=True)
    started_by:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Users.id", ondelete="SET NULL"), nullable=True)
    # active | ended | failed
    status:      Mapped[str]          = mapped_column(String(32), nullable=False, default="active")
    # Toplantı sonrası LangGraph Supervisor tarafından oluşturulan özet
    summary:     Mapped[str | None]   = mapped_column(Text, nullable=True)
    started_at:  Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    transcripts: Mapped[list["MeetingTranscript"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")


# ─── MO_MeetingTranscripts ─────────────────────────────────────
# Faz 4 — Sesli toplantı transcript satırları (konuşan + metin)

class MeetingTranscript(Base):
    __tablename__ = "MO_MeetingTranscripts"

    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    meeting_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("MO_Meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    # "user" veya membro_id string (sesli ajan kimliği)
    speaker:     Mapped[str]       = mapped_column(String(255), nullable=False)
    text:        Mapped[str]       = mapped_column(Text, nullable=False)
    created_at:  Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    meeting: Mapped["Meeting"] = relationship(back_populates="transcripts")
