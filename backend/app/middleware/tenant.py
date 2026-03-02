# backend/app/middleware/tenant.py
# Faz 1 — Tenant resolution middleware
# X-Tenant-Slug header'ından tenant_id'yi çözer ve request.state'e yazar

import uuid

import structlog
from fastapi import Request, Response
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.db.models import Tenant

log = structlog.get_logger()


async def tenant_middleware(request: Request, call_next) -> Response:
    """
    Her request başında:
    1. X-Tenant-Slug header'ından slug okur
    2. MO_Tenants'tan tenant_id resolve eder
    3. request.state.tenant_id ve request.state.tenant_slug set eder
    4. DB session'ında RLS bağlamını aktif eder

    /health, /metrics gibi internal endpoint'ler için slug zorunlu değil.
    """
    # request_id her requeste bir UUID ver (loglama için)
    request.state.request_id = str(uuid.uuid4())
    request.state.tenant_id   = None
    request.state.tenant_slug = None
    request.state.db          = None

    slug = (
        request.headers.get("X-Tenant-Slug")
        or request.headers.get("x-tenant-slug")
        or ""
    ).lower().strip()

    # Internal / health endpoint'leri atla
    skip_paths = {"/health", "/metrics", "/openapi.json", "/docs", "/redoc"}
    if request.url.path in skip_paths or not slug:
        return await call_next(request)

    # Tenant'ı çöz
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Tenant.id, Tenant.slug, Tenant.is_active)
            .where(Tenant.slug == slug)
        )
        row = result.first()

    if row is None or not row.is_active:
        log.warning("tenant_not_found", slug=slug, path=request.url.path)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"error": "tenant_not_found", "slug": slug},
        )

    request.state.tenant_id   = row.id
    request.state.tenant_slug = row.slug

    log.debug(
        "tenant_resolved",
        tenant_slug=slug,
        tenant_id=str(row.id),
        request_id=request.state.request_id,
    )

    return await call_next(request)
