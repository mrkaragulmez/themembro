# backend/app/api/v1/membros.py
# Faz 1 — Membro CRUD endpoint'leri (tenant izolasyonlu)

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Membro, SysMembro

router = APIRouter(prefix="/membros", tags=["membros"])


# ─── Şemalar ───────────────────────────────────────────────────

class MembroCreate(BaseModel):
    sys_membro_id: UUID
    name: str | None = None
    description: str | None = None
    extra_prompt: str | None = None
    tools_json: list | None = None

class MembroUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    tools_json: list | None = None
    is_active: bool | None = None

class MembroOut(BaseModel):
    id: UUID
    tenant_id: UUID
    sys_membro_id: UUID | None
    name: str
    description: str | None
    system_prompt: str | None
    extra_prompt: str | None
    tools_json: list | None
    is_active: bool

    class Config:
        from_attributes = True


# ─── Yardımcı: tenant_id doğrulama ────────────────────────────

def _require_tenant(request: Request) -> UUID:
    tid = request.state.tenant_id
    if not tid:
        raise HTTPException(status_code=400, detail="tenant_context_required")
    return tid


# ─── Endpoint'ler ──────────────────────────────────────────────

@router.get("/", response_model=list[MembroOut])
async def list_membros(request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id = _require_tenant(request)
    # RLS + explicit filter (çift güvenlik katmanı)
    rows = (await db.execute(
        select(Membro)
        .where(Membro.tenant_id == tenant_id, Membro.is_active.is_(True))
        .order_by(Membro.created_at.desc())
    )).scalars().all()
    return rows


@router.post("/", response_model=MembroOut, status_code=201)
async def create_membro(
    body: MembroCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _require_tenant(request)

    # SYS_Membros şablonunu getir
    sys_membro = (await db.execute(
        select(SysMembro).where(SysMembro.id == body.sys_membro_id, SysMembro.is_active.is_(True))
    )).scalar_one_or_none()

    if not sys_membro:
        raise HTTPException(status_code=404, detail="sys_membro_not_found")

    # system_prompt = base + extra_prompt wrap'i
    prompt_parts = [sys_membro.base_system_prompt or ""]
    if body.extra_prompt and body.extra_prompt.strip():
        prompt_parts.append(f"\n\nAdditional instructions:\n{body.extra_prompt.strip()}")
    system_prompt = "".join(prompt_parts).strip() or None

    membro = Membro(
        tenant_id=tenant_id,
        sys_membro_id=body.sys_membro_id,
        name=body.name or sys_membro.name,
        description=body.description or sys_membro.description,
        extra_prompt=body.extra_prompt,
        system_prompt=system_prompt,
        tools_json=body.tools_json or [],
    )
    db.add(membro)
    await db.flush()
    return membro


@router.get("/{membro_id}", response_model=MembroOut)
async def get_membro(membro_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id = _require_tenant(request)
    membro = (await db.execute(
        select(Membro).where(
            Membro.id == membro_id,
            Membro.tenant_id == tenant_id,
            Membro.is_active.is_(True),
        )
    )).scalar_one_or_none()

    if not membro:
        raise HTTPException(status_code=404, detail="membro_not_found")
    return membro


@router.patch("/{membro_id}", response_model=MembroOut)
async def update_membro(
    membro_id: UUID,
    body: MembroUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _require_tenant(request)
    membro = (await db.execute(
        select(Membro).where(
            Membro.id == membro_id,
            Membro.tenant_id == tenant_id,
            Membro.is_active.is_(True),
        )
    )).scalar_one_or_none()

    if not membro:
        raise HTTPException(status_code=404, detail="membro_not_found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(membro, field, value)

    # extra_prompt güncellendiyse system_prompt'u yeniden hesapla
    if body.extra_prompt is not None or body.description is not None:
        # sys_membro'yu lazy yükle
        sys_membro = await db.get(SysMembro, membro.sys_membro_id)
        if sys_membro:
            prompt_parts = [sys_membro.base_system_prompt or ""]
            ep = membro.extra_prompt
            if ep and ep.strip():
                prompt_parts.append(f"\n\nAdditional instructions:\n{ep.strip()}")
            membro.system_prompt = "".join(prompt_parts).strip() or None

    return membro


@router.delete("/{membro_id}", status_code=204)
async def delete_membro(
    membro_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _require_tenant(request)
    membro = (await db.execute(
        select(Membro).where(Membro.id == membro_id, Membro.tenant_id == tenant_id)
    )).scalar_one_or_none()

    if not membro:
        raise HTTPException(status_code=404, detail="membro_not_found")

    # Gerçek silme yerine soft delete
    membro.is_active = False
