# backend/app/api/v1/sys_membros.py
# Faz 6 — SYS_Membros ve SYS_Skills endpoint'leri (genel erişimli)
# Bu endpoint'ler auth gerektirmez (PUBLIC_PREFIXES'te kayıtlı).

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import SysMembro, SysSkill, SysMembroSkill, MoIntegration

router = APIRouter(prefix="/sys-membros", tags=["sys-membros"])


# ─── Şemalar ───────────────────────────────────────────────────

class SysMembroOut(BaseModel):
    id:                 UUID
    slug:               str
    name:               str
    role:               str
    description:        str | None
    is_active:          bool

    class Config:
        from_attributes = True


class SysSkillWithStatusOut(BaseModel):
    id:            UUID
    slug:          str
    name:          str
    description:   str | None
    is_self_skill: bool
    has_integration: bool   # is_self_skill ise her zaman True; değilse tenant'ın entegrasyonuna bakılır

    class Config:
        from_attributes = True


# ─── GET /sys-membros/ ─────────────────────────────────────────

@router.get("/", response_model=list[SysMembroOut])
async def list_sys_membros(db: AsyncSession = Depends(get_db)):
    """Tüm aktif sistem membro şablonlarını listeler. Auth gerektirmez."""
    rows = (await db.execute(
        select(SysMembro)
        .where(SysMembro.is_active.is_(True))
        .order_by(SysMembro.name)
    )).scalars().all()
    return rows


# ─── GET /sys-membros/{sys_membro_id}/skills ───────────────────

@router.get("/{sys_membro_id}/skills", response_model=list[SysSkillWithStatusOut])
async def get_sys_membro_skills(
    sys_membro_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Şablonun sahip olduğu skill'leri döndürür.
    - is_self_skill=True olan skill'lerde has_integration her zaman True.
    - Diğerlerinde: tenant'ın bu skill için bir MO_Integration kaydı varsa True.
    Auth opsiyoneldir; tenant bilinmiyorsa dış skill'ler has_integration=False döner.
    """
    # Şablonun var olup olmadığını doğrula
    sys_membro = (await db.execute(
        select(SysMembro).where(SysMembro.id == sys_membro_id, SysMembro.is_active.is_(True))
    )).scalar_one_or_none()

    if not sys_membro:
        raise HTTPException(status_code=404, detail="sys_membro_not_found")

    # Bu şablona ait skill_id'leri bul
    links = (await db.execute(
        select(SysMembroSkill.sys_skill_id)
        .where(SysMembroSkill.sys_membro_id == sys_membro_id)
    )).scalars().all()

    if not links:
        return []

    # Skill'leri getir
    skills = (await db.execute(
        select(SysSkill)
        .where(SysSkill.id.in_(links), SysSkill.is_active.is_(True))
        .order_by(SysSkill.name)
    )).scalars().all()

    # Tenant entegrasyonlarını kontrol et
    tenant_id = getattr(request.state, "tenant_id", None)
    integrated_skill_ids: set[str] = set()

    if tenant_id:
        integrations = (await db.execute(
            select(MoIntegration.sys_skill_id)
            .where(
                MoIntegration.tenant_id == tenant_id,
                MoIntegration.is_active.is_(True),
            )
        )).scalars().all()
        integrated_skill_ids = {str(sid) for sid in integrations}

    result = []
    for skill in skills:
        has_integration = skill.is_self_skill or str(skill.id) in integrated_skill_ids
        result.append(SysSkillWithStatusOut(
            id=skill.id,
            slug=skill.slug,
            name=skill.name,
            description=skill.description,
            is_self_skill=skill.is_self_skill,
            has_integration=has_integration,
        ))

    return result
