# backend/alembic/env.py
# Faz 1 — Async Alembic ortam konfigürasyonu (asyncpg driver)

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Uygulama modüllerini path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.db.models import Base  # tüm ORM modelleri buradan çekilir

# alembic ini logging konfigürasyonu
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData — autogenerate için
target_metadata = Base.metadata

# ─── Gerçek async DB URL ────────────────────────────────────────
DATABASE_URL = settings.database_url


def run_migrations_offline() -> None:
    """
    URL'yi doğrudan kullan; engine oluşturulmaz.
    Migration SQL dosyasına yazdırılır.
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Async engine ile migration çalıştır."""
    connectable = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
