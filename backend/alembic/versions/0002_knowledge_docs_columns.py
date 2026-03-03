"""0002_knowledge_docs_columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-03

MO_KnowledgeDocs tablosuna Faz 3 için eksik kolonları ekler:
  - content     (TEXT) — ham doküman metni
  - metadata    (JSONB) — indexleme metadata (chunk_count, hata vb.)

Aynı zamanda title VARCHAR(255) → VARCHAR(500) genişletilir.
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op


revision       = "0002"
down_revision  = "0001"
branch_labels  = None
depends_on     = None


def upgrade() -> None:
    # content kolonu — ham doküman metni
    op.add_column(
        "MO_KnowledgeDocs",
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
    )

    # metadata kolonu — JSONB, indexleme sonuç bilgisi
    op.add_column(
        "MO_KnowledgeDocs",
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
    )

    # title uzunluğunu 500'e çıkar
    op.alter_column(
        "MO_KnowledgeDocs",
        "title",
        existing_type=sa.String(255),
        type_=sa.String(500),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "MO_KnowledgeDocs",
        "title",
        existing_type=sa.String(500),
        type_=sa.String(255),
        existing_nullable=False,
    )
    op.drop_column("MO_KnowledgeDocs", "metadata")
    op.drop_column("MO_KnowledgeDocs", "content")
