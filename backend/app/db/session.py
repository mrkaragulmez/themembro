# backend/app/db/session.py
# Faz 1 — Async SQLAlchemy session + RLS tenant bağlamı kurulumu

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text, event

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.app_env == "development",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency. Her request için temiz bir session açar.
    request.state.tenant_id varsa RLS bağlamını SET LOCAL ile aktif eder.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    async with AsyncSessionLocal() as session:
        if tenant_id:
            await session.execute(
                text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")
            )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session(tenant_id: str | None = None):
    """
    Middleware ve exception handler gibi non-request bağlamlarda kullanılır.
    """
    async with AsyncSessionLocal() as session:
        if tenant_id:
            await session.execute(
                text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")
            )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
