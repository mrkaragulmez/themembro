"""0003_meetings

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-03

Faz 4 — WebRTC / LiveKit ses toplantısı tabloları oluşturulur:
  - MO_Meetings          — toplantı oturumları (LiveKit room bilgisi + özet)
  - MO_MeetingTranscripts — toplantı transkripsiyonları (konuşan + metin)
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op


revision      = "0003"
down_revision = "0002"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ─── MO_Meetings ───────────────────────────────────────────
    op.create_table(
        "MO_Meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("membro_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("MO_Membros.id", ondelete="SET NULL"), nullable=True),
        sa.Column("room_name", sa.String(255), nullable=False, unique=True),
        sa.Column("started_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("MO_Users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_MO_Meetings_tenant_id", "MO_Meetings", ["tenant_id"])
    op.create_index("ix_MO_Meetings_room_name",  "MO_Meetings", ["room_name"])

    # ─── MO_MeetingTranscripts ─────────────────────────────────
    op.create_table(
        "MO_MeetingTranscripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("MO_Tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("MO_Meetings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("speaker", sa.String(255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_MO_MeetingTranscripts_tenant_id",  "MO_MeetingTranscripts", ["tenant_id"])
    op.create_index("ix_MO_MeetingTranscripts_meeting_id", "MO_MeetingTranscripts", ["meeting_id"])
    op.create_index("ix_MO_MeetingTranscripts_created_at", "MO_MeetingTranscripts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_MO_MeetingTranscripts_created_at", table_name="MO_MeetingTranscripts")
    op.drop_index("ix_MO_MeetingTranscripts_meeting_id", table_name="MO_MeetingTranscripts")
    op.drop_index("ix_MO_MeetingTranscripts_tenant_id",  table_name="MO_MeetingTranscripts")
    op.drop_table("MO_MeetingTranscripts")

    op.drop_index("ix_MO_Meetings_room_name",  table_name="MO_Meetings")
    op.drop_index("ix_MO_Meetings_tenant_id",  table_name="MO_Meetings")
    op.drop_table("MO_Meetings")
