# backend/app/main.py
# Faz 1 + Faz 2 — FastAPI uygulama giriş noktası
# Faz 2 güncel: lifespan ile PostgreSQL checkpointer başlatılır;
# derlenen LangGraph grafiği app.state.graph üzerinden paylaşılır.

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
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
from mcp_server.server import create_mcp_app

log = structlog.get_logger()


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

app.include_router(auth_router.router,      prefix="/api/v1")
app.include_router(membros_router.router,   prefix="/api/v1")
app.include_router(chat_router.router,      prefix="/api/v1")
app.include_router(knowledge_router.router, prefix="/api/v1")

# ─── MCP Sunucusu (sub-application) ────────────────────────────────────────

app.mount("/mcp", create_mcp_app())

# ─── Health ────────────────────────────────────────────────────

@app.get("/health", tags=["infra"])
async def health():
    return {"status": "ok", "env": settings.app_env}
