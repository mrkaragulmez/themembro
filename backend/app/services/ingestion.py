# backend/app/services/ingestion.py
# Faz 3 — Doküman yutma (ingestion) pipeline
#
# Akış:
#   Ham metin
#     → RecursiveCharacterTextSplitter ile chunk'lara böl
#     → Her chunk için CF AI Gateway üzerinden OpenAI embedding al
#     → Milvus'a Partition Key (tenant_id) ile yaz
#     → PostgreSQL MO_KnowledgeDocs.status = "indexed"
#
# Güvenlik: tenant_id her zaman JWT'den gelir, asla parametreden alınmaz.

from __future__ import annotations

import uuid
import structlog
import httpx

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.milvus_client import get_milvus_client, COLLECTION_NAME
from app.db.models import KnowledgeDoc

log = structlog.get_logger()

# ─── Sabittler ──────────────────────────────────────────────────────────────

CHUNK_SIZE    = 512
CHUNK_OVERLAP = 64
EMBED_MODEL   = "text-embedding-3-small"
EMBED_DIM     = 1536

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


# ─── Embedding ──────────────────────────────────────────────────────────────

async def embed_texts(texts: list[str]) -> list[list[float]]:
    """CF AI Gateway üzerinden OpenAI embedding alır (batch).

    Args:
        texts: Embedding alınacak metin listesi.

    Returns:
        Her metin için EMBED_DIM boyutlu float listesi.
    """
    gateway_url = (
        f"{settings.cf_ai_gateway_url.rstrip('/')}/openai/v1/embeddings"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            gateway_url,
            headers={
                "Authorization":     f"Bearer {settings.cf_aig_token}",
                "Content-Type":      "application/json",
            },
            json={
                "model": EMBED_MODEL,
                "input": texts,
            },
        )
        resp.raise_for_status()

    data = resp.json()["data"]
    # OpenAI data listesi index'e göre sıralı döner
    return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


# ─── Ana Pipeline ───────────────────────────────────────────────────────────

async def ingest_document(
    *,
    doc_id: str,
    tenant_id: str,
    membro_id: str,
    title: str,
    content: str,
    db: AsyncSession,
) -> int:
    """Dokümanı chunk'lar, embed eder ve Milvus'a yazar.

    Args:
        doc_id:    PostgreSQL MO_KnowledgeDocs.id (UUID string)
        tenant_id: JWT'den gelen tenant UUID string
        membro_id: Hangi Membro'ya ait (UUID string, boş olabilir)
        title:     Doküman başlığı (loglama için)
        content:   Ham doküman metni
        db:        Aktif async SQLAlchemy session

    Returns:
        Milvus'a yazılan chunk sayısı.
    """
    log.info(
        "ingestion.start",
        doc_id=doc_id,
        tenant_id=tenant_id,
        content_len=len(content),
    )

    # ── 1. Chunking ─────────────────────────────────────────────
    chunks = _splitter.split_text(content)
    if not chunks:
        log.warning("ingestion.empty_chunks", doc_id=doc_id)
        return 0

    log.info("ingestion.chunked", doc_id=doc_id, chunk_count=len(chunks))

    # ── 2. Embedding (batch — tek API çağrısı) ───────────────────
    embeddings = await embed_texts(chunks)

    # ── 3. Milvus insert ────────────────────────────────────────
    milvus = get_milvus_client()

    rows = []
    for chunk_text, embedding in zip(chunks, embeddings):
        rows.append({
            "tenant_id":  tenant_id,
            "doc_id":     doc_id,
            "membro_id":  membro_id or "",
            "content":    chunk_text[:8192],   # VARCHAR max_length güvencesi
            "embedding":  embedding,
        })

    milvus.insert(collection_name=COLLECTION_NAME, data=rows)

    # ── 4. Neo4j GraphRAG: entity extraction + graph yazma ──────
    # NOT: PG status güncellemesinden ÖNCE çalışmalı; yoksa test "indexed"
    # görüp sil dediğinde chunk henüz yazılmamış olur (race condition).
    try:
        from app.services.graph_ingestion import graph_ingest_chunks
        from app.core.neo4j_client import get_neo4j_driver
        get_neo4j_driver()  # bağlı değilse RuntimeError → sessiz atla

        entity_count = await graph_ingest_chunks(
            chunks=chunks,
            doc_id=doc_id,
            tenant_id=tenant_id,
        )
        log.info(
            "ingestion.graph_done",
            doc_id=doc_id,
            entity_count=entity_count,
        )
    except RuntimeError:
        log.warning("ingestion.neo4j_not_connected", doc_id=doc_id)
    except Exception as exc:
        log.warning("ingestion.graph_failed", doc_id=doc_id, error=str(exc))

    # ── 5. PG status güncelle — Neo4j yazımı bittikten sonra ────
    await db.execute(
        update(KnowledgeDoc)
        .where(KnowledgeDoc.id == uuid.UUID(doc_id))
        .values(status="indexed", extra={"chunk_count": len(chunks)})
    )
    await db.commit()

    log.info(
        "ingestion.done",
        doc_id=doc_id,
        chunk_count=len(chunks),
    )
    return len(chunks)


# ─── Toplu Temizleme ────────────────────────────────────────────────────────

def delete_doc_vectors(*, doc_id: str, tenant_id: str) -> None:
    """Bir dokümanın tüm Milvus vektörlerini siler.

    Args:
        doc_id:   Silinecek doküman UUID'si
        tenant_id: Tenant UUID (güvenlik filtresi)
    """
    milvus = get_milvus_client()
    # tenant_id partition key + doc_id kombinasyonu — kesin izolasyon
    milvus.delete(
        collection_name=COLLECTION_NAME,
        filter=f'tenant_id == "{tenant_id}" && doc_id == "{doc_id}"',
    )
    log.info("ingestion.vectors_deleted", doc_id=doc_id, tenant_id=tenant_id)
