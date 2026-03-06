# backend/app/api/v1/integrations.py
# Faz 6 — Tenant entegrasyon yönetimi (3rd party API credential'ları)
# Credentials pgcrypto pgp_sym_encrypt ile şifreli olarak saklanır.

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import MoIntegration, SysSkill
from app.core.config import settings

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ─── Şemalar ───────────────────────────────────────────────────

class IntegrationCreate(BaseModel):
    sys_skill_id: UUID
    name:         str
    credentials:  dict     # şifrelenmemiş haliyle gelir, DB'ye şifreli yazılır

class IntegrationUpdate(BaseModel):
    name:        str | None = None
    credentials: dict | None = None
    is_active:   bool | None = None

class IntegrationOut(BaseModel):
    id:           UUID
    tenant_id:    UUID
    sys_skill_id: UUID
    skill_name:   str
    name:         str
    is_active:    bool

    class Config:
        from_attributes = True


# ─── Yardımcı ─────────────────────────────────────────────────

def _require_tenant(request: Request) -> UUID:
    tid = request.state.tenant_id
    if not tid:
        raise HTTPException(status_code=400, detail="tenant_context_required")
    return tid


# ─── GET /integrations/ ────────────────────────────────────────

@router.get("/", response_model=list[IntegrationOut])
async def list_integrations(request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id = _require_tenant(request)

    rows = (await db.execute(
        select(MoIntegration, SysSkill.name.label("skill_name"))
        .join(SysSkill, MoIntegration.sys_skill_id == SysSkill.id)
        .where(MoIntegration.tenant_id == tenant_id)
        .order_by(MoIntegration.created_at.desc())
    )).all()

    result = []
    for integration, skill_name in rows:
        result.append(IntegrationOut(
            id=integration.id,
            tenant_id=integration.tenant_id,
            sys_skill_id=integration.sys_skill_id,
            skill_name=skill_name,
            name=integration.name,
            is_active=integration.is_active,
        ))
    return result


# ─── POST /integrations/ ───────────────────────────────────────

@router.post("/", response_model=IntegrationOut, status_code=201)
async def create_integration(
    body: IntegrationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _require_tenant(request)

    # Skill var mı?
    skill = (await db.execute(
        select(SysSkill).where(SysSkill.id == body.sys_skill_id, SysSkill.is_active.is_(True))
    )).scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="sys_skill_not_found")

    # Self-skill'e entegrasyon oluşturulamaz (sisteme dahili)
    if skill.is_self_skill:
        raise HTTPException(status_code=400, detail="self_skill_does_not_require_integration")

    # credentials JSON → pgp_sym_encrypt
    credentials_json = json.dumps(body.credentials)
    enc_result = await db.execute(
        text("SELECT pgp_sym_encrypt(:val, :key)"),
        {"val": credentials_json, "key": settings.secret_key},
    )
    credentials_enc: str = enc_result.scalar()

    integration = MoIntegration(
        tenant_id=tenant_id,
        sys_skill_id=body.sys_skill_id,
        name=body.name,
        credentials_enc=credentials_enc,
        is_active=True,
    )
    db.add(integration)
    await db.flush()

    return IntegrationOut(
        id=integration.id,
        tenant_id=integration.tenant_id,
        sys_skill_id=integration.sys_skill_id,
        skill_name=skill.name,
        name=integration.name,
        is_active=integration.is_active,
    )


# ─── PATCH /integrations/{id} ─────────────────────────────────

@router.patch("/{integration_id}", response_model=IntegrationOut)
async def update_integration(
    integration_id: UUID,
    body: IntegrationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _require_tenant(request)

    row = (await db.execute(
        select(MoIntegration, SysSkill.name.label("skill_name"))
        .join(SysSkill, MoIntegration.sys_skill_id == SysSkill.id)
        .where(MoIntegration.id == integration_id, MoIntegration.tenant_id == tenant_id)
    )).first()

    if not row:
        raise HTTPException(status_code=404, detail="integration_not_found")

    integration, skill_name = row

    if body.name is not None:
        integration.name = body.name
    if body.is_active is not None:
        integration.is_active = body.is_active
    if body.credentials is not None:
        credentials_json = json.dumps(body.credentials)
        enc_result = await db.execute(
            text("SELECT pgp_sym_encrypt(:val, :key)"),
            {"val": credentials_json, "key": settings.secret_key},
        )
        integration.credentials_enc = enc_result.scalar()

    return IntegrationOut(
        id=integration.id,
        tenant_id=integration.tenant_id,
        sys_skill_id=integration.sys_skill_id,
        skill_name=skill_name,
        name=integration.name,
        is_active=integration.is_active,
    )


# ─── DELETE /integrations/{id} ────────────────────────────────

@router.delete("/{integration_id}", status_code=204)
async def delete_integration(
    integration_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _require_tenant(request)

    integration = (await db.execute(
        select(MoIntegration).where(
            MoIntegration.id == integration_id,
            MoIntegration.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    if not integration:
        raise HTTPException(status_code=404, detail="integration_not_found")

    await db.delete(integration)
