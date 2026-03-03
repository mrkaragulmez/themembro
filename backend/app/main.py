# backend/app/main.py
# Faz 1 + Faz 2 + Faz 4 + Faz 5 — FastAPI uygulama giriş noktası
# Faz 2 güncel: lifespan ile PostgreSQL checkpointer başlatılır;
# derlenen LangGraph grafiği app.state.graph üzerinden paylaşılır.
# Faz 4 güncel: meetings (sesli toplantı) router eklendi.
# Faz 5 güncel: structured logging konfigurasyonu + rate limiting eklendi.

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging_setup import configure_logging
from app.core.exception_handler import global_exception_handler
from app.core.checkpointer import init_pg_checkpointer, close_pg_checkpointer
from app.core.milvus_client import init_milvus, close_milvus
from app.core.neo4j_client import init_neo4j, close_neo4j
from app.agents.supervisor import compile_graph
from app.middleware.tenant import tenant_middleware
from app.middleware.auth import auth_middleware
from app.api.v1 import auth as auth_router
from app.api.v1 import membros as membros_router
from app.api.v1 import chat as chat_router
from app.api.v1 import knowledge as knowledge_router
from app.api.v1 import meetings as meetings_router
from mcp_server.server import create_mcp_app

# Faz 5: Loglama yapılandırılıyor — diğer import'lardan önce çağrılmalı
configure_logging()

log = structlog.get_logger()

# Faz 5: Rate Limiter — tenant bazlı key fonksiyonu
def _tenant_or_ip_key(request: Request) -> str:
    """Rate limiting anahtarı: tenant_id varsa tenant bazlı, yoksa IP bazlı."""
    tenant_id = getattr(request.state, "tenant_id", None)
    return str(tenant_id) if tenant_id else get_remote_address(request)

limiter = Limiter(key_func=_tenant_or_ip_key, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


# ─── Lifespan ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yaşam döngüsü.

    Startup:  PostgreSQL checkpointer + bağlantı havuzu açılır;
              LangGraph grafiği PG checkpointer ile derlenerek app.state'e yazılır.
    Shutdown: Bağlantı havuzu temiz biçimde kapatılır.
    """
    log.info("membro_api_starting", env=settings.app_env, domain=settings.app_domain)

    try:
        checkpointer = await init_pg_checkpointer(settings.pg_checkpoint_url)
        app.state.graph = compile_graph(checkpointer=checkpointer)
        log.info("langgraph_compiled_with_pg_checkpointer")
    except Exception as exc:
        # DB bağlantısı kurulamazsa (ör. test ortamı) in-memory fallback
        log.warning(
            "pg_checkpointer_unavailable_falling_back_to_memory",
            error=str(exc),
        )
        app.state.graph = compile_graph()  # MemorySaver

    # Milvus — bağlanamıyorsa uyar ama başlatmayı engelleme
    try:
        init_milvus()
    except Exception as exc:
        log.warning("milvus_unavailable", error=str(exc))

    # Neo4j — bağlanamıyorsa uyar ama başlatmayı engelleme
    try:
        await init_neo4j()
    except Exception as exc:
        log.warning("neo4j_unavailable", error=str(exc))

    yield

    await close_pg_checkpointer()
    close_milvus()
    await close_neo4j()
    log.info("membro_api_shutdown")


# ─── App ───────────────────────────────────────────────────────

app = FastAPI(
    title="Membro API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Faz 5: Rate limit aşımı için 429 handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ─── CORS ──────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(.*\.)?localhost(:\d+)?|https?://(.*\.)?themembro\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Faz 5: SlowAPI rate limit middleware
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)

# ─── Middleware zinciri (ters sıra: son eklenen ilk çalışır) ────
# Sıra önemli: tenant → auth

app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=tenant_middleware)

# ─── Global Exception Handler ──────────────────────────────────

app.add_exception_handler(Exception, global_exception_handler)

# ─── Router'lar ────────────────────────────────────────────────

app.include_router(auth_router.router,      prefix="/api/v1")
app.include_router(membros_router.router,   prefix="/api/v1")
app.include_router(chat_router.router,      prefix="/api/v1")
app.include_router(knowledge_router.router, prefix="/api/v1")
app.include_router(meetings_router.router,  prefix="/api/v1")

# ─── MCP Sunucusu (sub-application) ────────────────────────────────────────

app.mount("/mcp", create_mcp_app())

# ─── Health ────────────────────────────────────────────────────

@app.get("/health", tags=["infra"])
async def health():
    return {"status": "ok", "env": settings.app_env}
