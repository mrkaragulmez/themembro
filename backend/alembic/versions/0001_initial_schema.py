"""initial schema — MO_ tabloları ve RLS politikaları

Revision ID: 0001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

Faz 1 — Multi-tenant PostgreSQL şeması
"""
# backend/alembic/versions/0001_initial_schema.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Extensions ────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ─── MO_Tenants ────────────────────────────────────────────────
    op.create_table(
        "MO_Tenants",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,     server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name",       sa.String(255),                nullable=False),
        sa.Column("slug",       sa.String(100),                nullable=False,        unique=True),
        sa.Column("plan",       sa.String(50),                 nullable=False,        server_default="free"),
        sa.Column("is_active",  sa.Boolean(),                  nullable=False,        server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True),    nullable=False,        server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),    nullable=False,        server_default=sa.text("now()")),
    )
    op.create_index("ix_MO_Tenants_slug", "MO_Tenants", ["slug"], unique=True)

    # ─── MO_Users ──────────────────────────────────────────────────
    op.create_table(
        "MO_Users",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True,  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id",     postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email",         sa.String(255),                nullable=False),
        sa.Column("password_hash", sa.Text(),                     nullable=False),
        sa.Column("role",          sa.String(50),                 nullable=False,     server_default="member"),
        sa.Column("full_name",     sa.String(255),                nullable=True),
        sa.Column("is_active",     sa.Boolean(),                  nullable=False,     server_default="true"),
        sa.Column("created_at",    sa.DateTime(timezone=True),    nullable=False,     server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True),    nullable=False,     server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["MO_Tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("ix_MO_Users_tenant_id",    "MO_Users", ["tenant_id"])
    op.create_index("ix_MO_Users_tenant_email", "MO_Users", ["tenant_id", "email"], unique=True)

    # ─── MO_RefreshTokens ──────────────────────────────────────────
    op.create_table(
        "MO_RefreshTokens",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,     server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64),                 nullable=False,        unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True),    nullable=False),
        sa.Column("revoked",    sa.Boolean(),                  nullable=False,        server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True),    nullable=False,        server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"],   ["MO_Users.id"],   ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["MO_Tenants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_MO_RefreshTokens_token_hash", "MO_RefreshTokens", ["token_hash"], unique=True)
    op.create_index("ix_MO_RefreshTokens_user_id",    "MO_RefreshTokens", ["user_id"])

    # ─── MO_Membros ────────────────────────────────────────────────
    op.create_table(
        "MO_Membros",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True,   server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name",         sa.String(255),                nullable=False),
        sa.Column("description",  sa.Text(),                     nullable=True),
        sa.Column("avatar_url",   sa.Text(),                     nullable=True),
        sa.Column("system_prompt",sa.Text(),                     nullable=True),
        sa.Column("tools_json",   postgresql.JSONB(),            nullable=False,      server_default="[]"),
        sa.Column("is_active",    sa.Boolean(),                  nullable=False,      server_default="true"),
        sa.Column("created_by",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True),    nullable=False,      server_default=sa.text("now()")),
        sa.Column("updated_at",   sa.DateTime(timezone=True),    nullable=False,      server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"],  ["MO_Tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["MO_Users.id"],   ondelete="SET NULL"),
    )
    op.create_index("ix_MO_Membros_tenant_id", "MO_Membros", ["tenant_id"])

    # ─── MO_Conversations ──────────────────────────────────────────
    op.create_table(
        "MO_Conversations",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,     server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id",  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membro_id",  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title",      sa.String(255),                nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),    nullable=False,       server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),    nullable=False,       server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["MO_Tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"],   ["MO_Users.id"],   ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["membro_id"], ["MO_Membros.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_MO_Conversations_tenant_id", "MO_Conversations", ["tenant_id"])
    op.create_index("ix_MO_Conversations_user_id",   "MO_Conversations", ["user_id"])

    # ─── MO_Messages ───────────────────────────────────────────────
    op.create_table(
        "MO_Messages",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role",            sa.String(20),                 nullable=False),
        sa.Column("content",         sa.Text(),                     nullable=False),
        sa.Column("metadata_json",   postgresql.JSONB(),            nullable=False,   server_default="{}"),
        sa.Column("created_at",      sa.DateTime(timezone=True),    nullable=False,   server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["conversation_id"], ["MO_Conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"],       ["MO_Tenants.id"],       ondelete="CASCADE"),
    )
    op.create_index("ix_MO_Messages_conversation_id", "MO_Messages", ["conversation_id"])
    op.create_index("ix_MO_Messages_tenant_id",       "MO_Messages", ["tenant_id"])

    # ─── MO_KnowledgeDocs ──────────────────────────────────────────
    op.create_table(
        "MO_KnowledgeDocs",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True,    server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membro_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title",       sa.String(255),                nullable=False),
        sa.Column("source_url",  sa.Text(),                     nullable=True),
        sa.Column("status",      sa.String(50),                 nullable=False,      server_default="pending"),
        sa.Column("chunk_count", sa.Integer(),                  nullable=False,      server_default="0"),
        sa.Column("created_at",  sa.DateTime(timezone=True),    nullable=False,      server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True),    nullable=False,      server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["MO_Tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["membro_id"], ["MO_Membros.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_MO_KnowledgeDocs_tenant_id", "MO_KnowledgeDocs", ["tenant_id"])

    # ─── MO_Eventlog ───────────────────────────────────────────────
    op.create_table(
        "MO_Eventlog",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True,   server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id",    postgresql.UUID(as_uuid=True), nullable=True),   # nullable: sistem hataları
        sa.Column("user_id",      postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id",   sa.String(36),                 nullable=True),
        sa.Column("level",        sa.String(20),                 nullable=False,     server_default="ERROR"),
        sa.Column("event_type",   sa.String(100),                nullable=False),
        sa.Column("message",      sa.Text(),                     nullable=False),
        sa.Column("detail",       postgresql.JSONB(),            nullable=False,     server_default="{}"),
        sa.Column("path",         sa.Text(),                     nullable=True),
        sa.Column("method",       sa.String(10),                 nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True),    nullable=False,     server_default=sa.text("now()")),
    )
    op.create_index("ix_MO_Eventlog_tenant_id",  "MO_Eventlog", ["tenant_id"])
    op.create_index("ix_MO_Eventlog_created_at", "MO_Eventlog", ["created_at"])

    # ─── Row-Level Security — tüm tenant-scoped tablolar ──────────
    tenant_tables = [
        "MO_Users",
        "MO_RefreshTokens",
        "MO_Membros",
        "MO_Conversations",
        "MO_Messages",
        "MO_KnowledgeDocs",
    ]

    for tbl in tenant_tables:
        # RLS aktif et ve superuser dahil zorla
        op.execute(f'ALTER TABLE "{tbl}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{tbl}" FORCE ROW LEVEL SECURITY')

        # Okuma politikası
        op.execute(f"""
            CREATE POLICY "{tbl}_tenant_isolation_select"
            ON "{tbl}"
            FOR SELECT
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            )
        """)

        # Yazma politikası (INSERT)
        op.execute(f"""
            CREATE POLICY "{tbl}_tenant_isolation_insert"
            ON "{tbl}"
            FOR INSERT
            WITH CHECK (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            )
        """)

        # Güncelleme politikası
        op.execute(f"""
            CREATE POLICY "{tbl}_tenant_isolation_update"
            ON "{tbl}"
            FOR UPDATE
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            )
        """)

        # Silme politikası
        op.execute(f"""
            CREATE POLICY "{tbl}_tenant_isolation_delete"
            ON "{tbl}"
            FOR DELETE
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            )
        """)

    # ─── MO_Eventlog özel RLS ──────────────────────────────────────
    # tenant NULL olan satırlar (sistem hataları) sadece super-admin görür
    op.execute('ALTER TABLE "MO_Eventlog" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "MO_Eventlog" FORCE ROW LEVEL SECURITY')

    op.execute("""
        CREATE POLICY "MO_Eventlog_tenant_select"
        ON "MO_Eventlog"
        FOR SELECT
        USING (
            tenant_id IS NULL
            OR tenant_id::text = current_setting('app.current_tenant_id', true)
        )
    """)

    op.execute("""
        CREATE POLICY "MO_Eventlog_insert"
        ON "MO_Eventlog"
        FOR INSERT
        WITH CHECK (true)
    """)

    # ─── MO_Tenants — RLS YOK (global lookup tablosu) ───────────
    # Tenant middleware doğrudan bu tabloyu okur; uygulama kullanıcısı
    # SELECT yetkisine sahip olmalı ama RLS bypass gerekmez.


def downgrade() -> None:
    tables = [
        "MO_Eventlog",
        "MO_KnowledgeDocs",
        "MO_Messages",
        "MO_Conversations",
        "MO_Membros",
        "MO_RefreshTokens",
        "MO_Users",
        "MO_Tenants",
    ]
    for tbl in tables:
        op.execute(f'DROP TABLE IF EXISTS "{tbl}" CASCADE')
