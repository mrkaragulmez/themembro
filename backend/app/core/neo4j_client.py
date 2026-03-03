# backend/app/core/neo4j_client.py
# Faz 3 — Neo4j graph veritabanı sürücüsü yaşam döngüsü
#
# GraphRAG için varlık-ilişki ağını barındırır.
# AsyncDriver, uygulama startup'ında açılır, shutdown'da kapatılır.

from __future__ import annotations

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.core.config import settings

log = structlog.get_logger()

# ─── Singleton ──────────────────────────────────────────────────────────────

_driver: AsyncDriver | None = None


def get_neo4j_driver() -> AsyncDriver:
    """Mevcut Neo4j sürücüsünü döndürür."""
    if _driver is None:
        raise RuntimeError("Neo4j sürücüsü henüz başlatılmadı. init_neo4j() çağrılmalı.")
    return _driver


# ─── Başlatma / Kapatma ─────────────────────────────────────────────────────

async def init_neo4j() -> AsyncDriver:
    """Neo4j async sürücüsünü oluşturur ve bağlantıyı doğrular."""
    global _driver

    log.info("neo4j.init_start", uri=settings.neo4j_uri)

    _driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        max_connection_pool_size=20,
    )

    # Bağlantı doğrulama
    await _driver.verify_connectivity()

    # Temel constraint + index'ler (idempotent)
    await _setup_schema(_driver)

    log.info("neo4j.init_done")
    return _driver


async def close_neo4j() -> None:
    """Neo4j sürücüsünü kapatır."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        log.info("neo4j.closed")


# ─── Schema Kurulumu ────────────────────────────────────────────────────────

async def _setup_schema(driver: AsyncDriver) -> None:
    """Temel GraphRAG node constraint ve index'lerini oluşturur (idempotent)."""
    queries = [
        # Her tenant izolasyonu için compound constraint
        """
        CREATE CONSTRAINT doc_chunk_unique IF NOT EXISTS
        FOR (c:Chunk) REQUIRE (c.tenant_id, c.chunk_id) IS UNIQUE
        """,
        """
        CREATE CONSTRAINT entity_unique IF NOT EXISTS
        FOR (e:Entity) REQUIRE (e.tenant_id, e.name, e.type) IS UNIQUE
        """,
        """
        CREATE INDEX chunk_tenant IF NOT EXISTS
        FOR (c:Chunk) ON (c.tenant_id)
        """,
        """
        CREATE INDEX entity_tenant IF NOT EXISTS
        FOR (e:Entity) ON (e.tenant_id)
        """,
    ]

    async with driver.session() as session:
        for q in queries:
            try:
                await session.run(q)
            except Exception as exc:
                # Constraint zaten varsa hata fırlatabiliyor — güvenle atla
                log.debug("neo4j.schema_skip", reason=str(exc)[:80])

    log.info("neo4j.schema_ready")
