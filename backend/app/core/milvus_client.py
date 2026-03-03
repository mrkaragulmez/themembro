# backend/app/core/milvus_client.py
# Faz 3 — Milvus vektör veritabanı istemcisi ve koleksiyon yönetimi
#
# Strateji: Partition Key (tenant_id) — sınırsız tenant, tek koleksiyon.
# Güvenlik zorunluluğu: tüm sorgularda filter="tenant_id == '{id}'" kullanılmalı.

from __future__ import annotations

import structlog
from pymilvus import MilvusClient, DataType

from app.core.config import settings

log = structlog.get_logger()

# ─── Sabitler ───────────────────────────────────────────────────────────────

COLLECTION_NAME   = "knowledge_base"
EMBEDDING_DIM     = 1536          # OpenAI text-embedding-3-small
NUM_PARTITIONS    = 64            # tenant hash dağılımı
INDEX_METRIC      = "COSINE"

# ─── Singleton ──────────────────────────────────────────────────────────────

_client: MilvusClient | None = None


def get_milvus_client() -> MilvusClient:
    """Mevcut Milvus istemcisini döndürür. init_milvus() öncesinde çağrılmamalı."""
    if _client is None:
        raise RuntimeError("Milvus istemcisi henüz başlatılmadı. init_milvus() çağrılmalı.")
    return _client


# ─── Başlatma ───────────────────────────────────────────────────────────────

def init_milvus() -> MilvusClient:
    """Milvus bağlantısını açar ve koleksiyonu idempotent şekilde kurar.

    Koleksiyon yoksa oluşturur; varsa atlar.
    IVF_FLAT indeksi oluşturulduktan sonra koleksiyonu yükler.
    """
    global _client

    log.info("milvus.init_start", uri=settings.milvus_uri)
    _client = MilvusClient(uri=settings.milvus_uri)

    _ensure_collection(_client)

    log.info("milvus.init_done", collection=COLLECTION_NAME)
    return _client


def close_milvus() -> None:
    """Milvus bağlantısını kapatır."""
    global _client
    if _client is not None:
        # MilvusClient.close() — bağlantı serbest bırakılır
        try:
            _client.close()
        except Exception:
            pass
        _client = None
        log.info("milvus.closed")


# ─── Koleksiyon Kurulumu ────────────────────────────────────────────────────

def _ensure_collection(client: MilvusClient) -> None:
    """Koleksiyonu ve indexi idempotent şekilde oluşturur."""

    if client.has_collection(COLLECTION_NAME):
        log.info("milvus.collection_exists", collection=COLLECTION_NAME)
        # Koleksiyonun yüklü olduğundan emin ol
        client.load_collection(COLLECTION_NAME)
        return

    log.info("milvus.creating_collection", collection=COLLECTION_NAME)

    # ── Şema ────────────────────────────────────────────────────
    schema = client.create_schema(auto_id=True, enable_dynamic_field=False)

    schema.add_field(
        field_name="id",
        datatype=DataType.INT64,
        is_primary=True,
        auto_id=True,
    )
    schema.add_field(
        field_name="tenant_id",
        datatype=DataType.VARCHAR,
        max_length=64,
        is_partition_key=True,   # multi-tenancy: otomatik hash dağılımı
    )
    schema.add_field(
        field_name="doc_id",
        datatype=DataType.VARCHAR,
        max_length=64,           # PostgreSQL UUID
    )
    schema.add_field(
        field_name="membro_id",
        datatype=DataType.VARCHAR,
        max_length=64,
    )
    schema.add_field(
        field_name="content",
        datatype=DataType.VARCHAR,
        max_length=8192,
    )
    schema.add_field(
        field_name="embedding",
        datatype=DataType.FLOAT_VECTOR,
        dim=EMBEDDING_DIM,
    )

    # ── İndeks parametreleri ────────────────────────────────────
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="IVF_FLAT",
        metric_type=INDEX_METRIC,
        params={"nlist": 128},
    )

    # ── Oluştur ve yükle ────────────────────────────────────────
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params,
        num_partitions=NUM_PARTITIONS,
    )

    client.load_collection(COLLECTION_NAME)
    log.info("milvus.collection_created", collection=COLLECTION_NAME)
