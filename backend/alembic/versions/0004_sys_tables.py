"""SYS tabloları ve MO_Integrations — seed verisiyle

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-05 00:00:00.000000

Faz 6 — SYS_Membros, SYS_Skills, SYS_Capabilities, SYS_MembroSkills, MO_Integrations
         MO_Membros tablosuna sys_membro_id (NOT NULL) ve extra_prompt eklendi.
"""
# backend/alembic/versions/0004_sys_tables.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ─── SYS_Membros ───────────────────────────────────────────────
    op.create_table(
        "SYS_Membros",
        sa.Column("id",                 postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("slug",               sa.String(100),                nullable=False),
        sa.Column("name",               sa.String(255),                nullable=False),
        sa.Column("role",               sa.String(255),                nullable=False),
        sa.Column("description",        sa.Text(),                     nullable=True),
        sa.Column("base_system_prompt", sa.Text(),                     nullable=True),
        sa.Column("is_active",          sa.Boolean(),                  nullable=False, server_default="true"),
    )
    op.create_index("ix_SYS_Membros_slug", "SYS_Membros", ["slug"], unique=True)

    # ─── SYS_Skills ────────────────────────────────────────────────
    op.create_table(
        "SYS_Skills",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("slug",          sa.String(100),                nullable=False),
        sa.Column("name",          sa.String(255),                nullable=False),
        sa.Column("description",   sa.Text(),                     nullable=True),
        sa.Column("is_self_skill", sa.Boolean(),                  nullable=False, server_default="false"),
        sa.Column("is_active",     sa.Boolean(),                  nullable=False, server_default="true"),
    )
    op.create_index("ix_SYS_Skills_slug", "SYS_Skills", ["slug"], unique=True)

    # ─── SYS_Capabilities ──────────────────────────────────────────
    op.create_table(
        "SYS_Capabilities",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("skill_id",      postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug",          sa.String(100),                nullable=False),
        sa.Column("name",          sa.String(255),                nullable=False),
        sa.Column("description",   sa.Text(),                     nullable=True),
        sa.Column("config_schema", postgresql.JSONB(),            nullable=True),
        sa.Column("is_active",     sa.Boolean(),                  nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["skill_id"], ["SYS_Skills.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_SYS_Capabilities_slug",     "SYS_Capabilities", ["slug"],     unique=True)
    op.create_index("ix_SYS_Capabilities_skill_id", "SYS_Capabilities", ["skill_id"])

    # ─── SYS_MembroSkills ──────────────────────────────────────────
    op.create_table(
        "SYS_MembroSkills",
        sa.Column("sys_membro_id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("sys_skill_id",  postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.ForeignKeyConstraint(["sys_membro_id"], ["SYS_Membros.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sys_skill_id"],  ["SYS_Skills.id"],  ondelete="CASCADE"),
    )

    # ─── MO_Integrations ───────────────────────────────────────────
    op.create_table(
        "MO_Integrations",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sys_skill_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name",            sa.String(255),                nullable=False),
        sa.Column("credentials_enc", sa.Text(),                     nullable=True),
        sa.Column("is_active",       sa.Boolean(),                  nullable=False, server_default="true"),
        sa.Column("created_at",      sa.DateTime(timezone=True),    nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",      sa.DateTime(timezone=True),    nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"],    ["MO_Tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sys_skill_id"], ["SYS_Skills.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_MO_Integrations_tenant_id",    "MO_Integrations", ["tenant_id"])
    op.create_index("ix_MO_Integrations_sys_skill_id", "MO_Integrations", ["sys_skill_id"])

    # RLS — MO_Integrations (tenant izolasyonu)
    op.execute('ALTER TABLE "MO_Integrations" ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY tenant_isolation ON "MO_Integrations"
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # ─── MO_Membros: yeni sütunlar ─────────────────────────────────
    # Önce nullable olarak ekle, sonra NOT NULL yapacağız
    op.add_column("MO_Membros", sa.Column("sys_membro_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("MO_Membros", sa.Column("extra_prompt",  sa.Text(), nullable=True))

    # ─── SEED: SYS_Skills ──────────────────────────────────────────
    conn.execute(sa.text("""
        INSERT INTO "SYS_Skills" (id, slug, name, description, is_self_skill, is_active)
        VALUES (
            uuid_generate_v4(),
            'memory',
            'Memory',
            'Membro''un kendi bilgi bankası. Vektör tabanlı belge araması ve hatırlama yeteneği. Dış entegrasyon gerektirmez.',
            true,
            true
        )
    """))

    # ─── SEED: SYS_Capabilities ────────────────────────────────────
    conn.execute(sa.text("""
        INSERT INTO "SYS_Capabilities" (id, skill_id, slug, name, description, config_schema, is_active)
        SELECT
            uuid_generate_v4(),
            s.id,
            'knowledge_search',
            'Knowledge Search',
            'Membro''nun bilgi bankasında vektör benzerlik araması yapar. RAG pipeline ile bağlantılı.',
            '{"max_results": 5, "similarity_threshold": 0.7}'::jsonb,
            true
        FROM "SYS_Skills" s WHERE s.slug = 'memory'
    """))

    # ─── SEED: SYS_Membros (12 şablon) ────────────────────────────
    membros_seed = [
        {
            "slug":        "the-pm",
            "name":        "the.PM",
            "role":        "Proje Yöneticisi",
            "description": "Projelerini planlar, takip eder ve raporlar.",
            "prompt":      (
                "You are a skilled Project Manager. "
                "Help plan projects, create timelines, track milestones, identify blockers, "
                "and generate concise status reports. "
                "Be structured, proactive, and data-driven in every response."
            ),
        },
        {
            "slug":        "the-ba",
            "name":        "the.BA",
            "role":        "İş Analisti",
            "description": "Gereksinimleri analiz eder, süreçleri belgeler.",
            "prompt":      (
                "You are an expert Business Analyst. "
                "Gather and analyze requirements, document processes, identify gaps, "
                "and translate business needs into clear technical specifications. "
                "Be thorough, precise, and methodical."
            ),
        },
        {
            "slug":        "the-tester",
            "name":        "the.TESTER",
            "role":        "QA Uzmanı",
            "description": "Test senaryoları yazar, hataları bulur.",
            "prompt":      (
                "You are a seasoned QA Engineer. "
                "Write comprehensive test scenarios, identify bugs, evaluate test coverage, "
                "and ensure software quality. "
                "Think critically, cover edge cases, and document findings clearly."
            ),
        },
        {
            "slug":        "the-asistan",
            "name":        "the.ASİSTAN",
            "role":        "Sanal Asistan",
            "description": "Takvim, e-posta ve idari işleri yönetir.",
            "prompt":      (
                "You are a reliable Virtual Assistant. "
                "Manage calendars, draft and organize emails, coordinate administrative tasks, "
                "and keep operations running smoothly. "
                "Be efficient, polite, and proactive."
            ),
        },
        {
            "slug":        "the-copywriter",
            "name":        "the.COPYWRITER",
            "role":        "İçerik Yazarı",
            "description": "İkna edici metinler ve içerikler üretir.",
            "prompt":      (
                "You are a creative Copywriter. "
                "Craft persuasive texts, compelling content, and effective marketing copy. "
                "Always match the tone to the target audience and prioritize clarity and impact."
            ),
        },
        {
            "slug":        "the-marketer",
            "name":        "the.MARKETER",
            "role":        "Dijital Pazarlamacı",
            "description": "Kampanyaları planlar ve analiz eder.",
            "prompt":      (
                "You are a Digital Marketing Specialist. "
                "Plan and evaluate campaigns, analyze performance metrics, "
                "suggest targeting strategies, and interpret analytics. "
                "Be strategic, data-driven, and conversion-focused."
            ),
        },
        {
            "slug":        "the-influencer",
            "name":        "the.INFLUENCER",
            "role":        "Sosyal Medya Uzmanı",
            "description": "Sosyal medya stratejisi ve içerik takvimi.",
            "prompt":      (
                "You are a Social Media Expert. "
                "Develop social strategies, create content calendars, analyze engagement metrics, "
                "and advise on platform-specific best practices. "
                "Be creative, trend-aware, and brand-consistent."
            ),
        },
        {
            "slug":        "the-developer",
            "name":        "the.DEVELOPER",
            "role":        "Yazılım Geliştirici",
            "description": "Teknik görevleri kodlar ve belgeler.",
            "prompt":      (
                "You are a proficient Software Developer. "
                "Write, review, and document code. Solve technical problems, "
                "explain complex concepts clearly, and assist with architecture decisions. "
                "Be precise, practical, and thorough."
            ),
        },
        {
            "slug":        "the-psychologist",
            "name":        "the.PSİKOLOG",
            "role":        "Davranış Danışmanı",
            "description": "Ekip dinamikleri ve iletişim önerileri.",
            "prompt":      (
                "You are a Behavioral Consultant with expertise in organizational psychology. "
                "Advise on team dynamics, communication patterns, conflict resolution, "
                "and individual motivation. "
                "Be empathetic, insightful, and evidence-based."
            ),
        },
        {
            "slug":        "the-lawyer",
            "name":        "the.LAWYER",
            "role":        "Hukuki Danışman",
            "description": "Sözleşme taslakları ve hukuki inceleme.",
            "prompt":      (
                "You are a Legal Advisor. "
                "Draft contract templates, review documents, identify risks, "
                "and explain legal concepts in plain language. "
                "Always clarify that your responses are informational, not formal legal advice."
            ),
        },
        {
            "slug":        "the-tercuman",
            "name":        "the.TERCÜMAN",
            "role":        "Tercüman",
            "description": "Çok dilli çeviri ve yerelleştirme.",
            "prompt":      (
                "You are a multilingual Translator and localization expert. "
                "Translate accurately, adapt content culturally, "
                "and ensure natural-sounding output in the target language. "
                "Be faithful to the source while ensuring natural flow."
            ),
        },
        {
            "slug":        "the-sales",
            "name":        "the.SALES",
            "role":        "Satış Temsilcisi",
            "description": "CRM takibi, prospecting ve pitch hazırlığı.",
            "prompt":      (
                "You are an experienced Sales Representative. "
                "Assist with CRM tracking, prospecting, pitch preparation, "
                "objection handling, and deal strategy. "
                "Be persuasive, empathetic, and goal-oriented."
            ),
        },
    ]

    for m in membros_seed:
        conn.execute(
            sa.text("""
                INSERT INTO "SYS_Membros" (id, slug, name, role, description, base_system_prompt, is_active)
                VALUES (uuid_generate_v4(), :slug, :name, :role, :description, :prompt, true)
            """),
            m,
        )

    # ─── SEED: SYS_MembroSkills (tüm membro'lara memory skill'i) ──
    conn.execute(sa.text("""
        INSERT INTO "SYS_MembroSkills" (sys_membro_id, sys_skill_id)
        SELECT sm.id, sk.id
        FROM "SYS_Membros" sm
        CROSS JOIN "SYS_Skills" sk
        WHERE sk.slug = 'memory'
    """))

    # ─── MO_Membros: sys_membro_id NOT NULL constraint ─────────────
    # Mevcut kayıt yoksa direkt NOT NULL yapılabilir
    op.alter_column("MO_Membros", "sys_membro_id", nullable=False)
    op.create_foreign_key(
        "fk_mo_membros_sys_membro_id",
        "MO_Membros", "SYS_Membros",
        ["sys_membro_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_MO_Membros_sys_membro_id", "MO_Membros", ["sys_membro_id"])


def downgrade() -> None:
    op.drop_constraint("fk_mo_membros_sys_membro_id", "MO_Membros", type_="foreignkey")
    op.drop_index("ix_MO_Membros_sys_membro_id", "MO_Membros")
    op.drop_column("MO_Membros", "sys_membro_id")
    op.drop_column("MO_Membros", "extra_prompt")

    op.drop_table("MO_Integrations")
    op.drop_table("SYS_MembroSkills")
    op.drop_table("SYS_Capabilities")
    op.drop_table("SYS_Skills")
    op.drop_table("SYS_Membros")
