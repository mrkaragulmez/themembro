# backend/app/main.py
# Faz 1 + Faz 2 — FastAPI uygulama giriş noktası

import uuid
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exception_handler import global_exception_handler
from app.middleware.tenant import tenant_middleware
from app.middleware.auth import auth_middleware
from app.api.v1 import auth as auth_router
from app.api.v1 import membros as membros_router
from app.api.v1 import chat as chat_router
from mcp_server.server import create_mcp_app

log = structlog.get_logger()

# ─── App ───────────────────────────────────────────────────────

app = FastAPI(
    title="Membro API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ─── CORS ──────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(.*\.)?localhost(:\d+)?|https?://(.*\.)?themembro\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Middleware zinciri (ters sıra: son eklenen ilk çalışır) ────
# Sıra önemli: tenant → auth

app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=tenant_middleware)

# ─── Global Exception Handler ──────────────────────────────────

app.add_exception_handler(Exception, global_exception_handler)

# ─── Router'lar ────────────────────────────────────────────────

app.include_router(auth_router.router,    prefix="/api/v1")
app.include_router(membros_router.router, prefix="/api/v1")
app.include_router(chat_router.router,    prefix="/api/v1")

# ─── MCP Sunucusu (sub-application) ────────────────────────────────────────

app.mount("/mcp", create_mcp_app())

# ─── Health ────────────────────────────────────────────────────

@app.get("/health", tags=["infra"])
async def health():
    return {"status": "ok", "env": settings.app_env}


# ─── Startup / Shutdown ────────────────────────────────────────

@app.on_event("startup")
async def startup():
    log.info("membro_api_started", env=settings.app_env, domain=settings.app_domain)


@app.on_event("shutdown")
async def shutdown():
    log.info("membro_api_shutdown")
