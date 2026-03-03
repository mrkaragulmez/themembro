# backend/app/core/checkpointer.py
# Faz 2 — LangGraph PostgreSQL Checkpointer yaşam döngüsü yönetimi
#
# AsyncConnectionPool + AsyncPostgresSaver kombinasyonu ile konuşma durumu
# PostgreSQL'de kalıcı olarak saklanır. Pool uygulama startup'ında açılır,
# shutdown'da kapatılır. compile_graph() bu checkpointer ile çağrılmalıdır.

from __future__ import annotations

import structlog
from typing import TYPE_CHECKING

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

if TYPE_CHECKING:
    pass

log = structlog.get_logger()

# ─── Module-level singleton'lar ─────────────────────────────────────────────
_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None


async def init_pg_checkpointer(conn_string: str) -> AsyncPostgresSaver:
    """PostgreSQL bağlantı havuzunu ve LangGraph checkpointer'ı başlatır.

    Args:
        conn_string: psycopg v3 uyumlu bağlantı dizesi
                     Örnek: postgresql://user:pass@host:5432/db

    Returns:
        Kurulum tamamlanmış AsyncPostgresSaver örneği.
    """
    global _pool, _checkpointer

    log.info("checkpointer.init_start")

    # psycopg v3 async pool — autocommit + prepare_threshold=0 LangGraph zorunluluğu
    _pool = AsyncConnectionPool(
        conninfo=conn_string,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,   # langgraph-checkpoint-postgres gereksinimi
        },
        max_size=20,
        open=False,  # açılışı explicit olarak yönetiyoruz
    )
    await _pool.open()

    _checkpointer = AsyncPostgresSaver(_pool)

    # Checkpoint tablolarını oluşturur (idempotent — varsa atlar)
    await _checkpointer.setup()

    log.info("checkpointer.init_done", pool_max_size=20)
    return _checkpointer


async def close_pg_checkpointer() -> None:
    """Bağlantı havuzunu kapatır. Uygulama shutdown'ında çağrılmalıdır."""
    global _pool, _checkpointer

    if _pool is not None:
        await _pool.close()
        _pool = None
        _checkpointer = None
        log.info("checkpointer.closed")


def get_checkpointer() -> AsyncPostgresSaver | None:
    """Mevcut checkpointer singleton'ını döndürür.

    Henüz init edilmemişse None döner (geliştirme modunda fallback için).
    """
    return _checkpointer
