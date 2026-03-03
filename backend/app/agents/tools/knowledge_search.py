# backend/app/agents/tools/knowledge_search.py
# Faz 3 — Bilgi bankası arama aracı (Milvus vektör + CF AI Gateway embedding)
#
# Güvenlik zorunluluğu: her sorguda tenant_id filtresi kullanılır.
# tenant_id asla kullanıcı girdisinden alınmaz, ToolInput.tenant_id'den gelir.

from __future__ import annotations

import structlog
import httpx
from pydantic import Field

from app.agents.tools.base import BaseTool, ToolInput, ToolOutput, register_tool
from app.core.config import settings
from app.core.milvus_client import get_milvus_client, COLLECTION_NAME, INDEX_METRIC
from app.services.ingestion import embed_texts

log = structlog.get_logger()


class KnowledgeSearchInput(ToolInput):
    query: str = Field(..., description="Aranacak metin sorgusu")
    top_k: int = Field(default=5, description="Döndürülecek maksimum sonuç sayısı")
    membro_id: str | None = Field(default=None, description="Sadece bu Membro'ya ait dokümanlar (opsiyonel)")


class KnowledgeSearchTool(BaseTool):
    """Bilgi bankasını Milvus vektör benzerliği ile arar.

    Partition Key (tenant_id) stratejisi: her sorgu yalnızca
    ilgili tenant'ın verilerini döndürür.
    """

    name = "search_knowledge_base"
    description = (
        "Membro'nun bilgi bankasında semantik arama yapar. "
        "Şirket politikaları, ürün bilgileri, sıkça sorulan sorular gibi "
        "yapılandırılmış verilere erişmek için kullanılır."
    )

    async def run(self, arguments: dict) -> ToolOutput:  # type: ignore[override]
        input_data = KnowledgeSearchInput(**arguments)
        tenant_id  = input_data.tenant_id

        log.info(
            "knowledge_search.run",
            tenant_id=tenant_id,
            query=input_data.query[:80],
            top_k=input_data.top_k,
        )

        try:
            milvus = get_milvus_client()
        except RuntimeError:
            # Milvus henüz başlatılmamış (test ortamı)
            return ToolOutput(success=False, result={"chunks": [], "message": "Milvus bağlı değil."})

        # ── 1. Query embedding ───────────────────────────────────
        try:
            [query_embedding] = await embed_texts([input_data.query])
        except Exception as exc:
            log.error("knowledge_search.embed_error", error=str(exc))
            return ToolOutput(success=False, result={"chunks": [], "message": f"Embedding hatası: {exc}"})

        # ── 2. Milvus arama ─────────────────────────────────────
        # Güvenlik: tenant_id filtresi zorunlu — asla kaldırılmamalı
        search_filter = f'tenant_id == "{tenant_id}"'
        if input_data.membro_id:
            search_filter += f' && membro_id == "{input_data.membro_id}"'

        try:
            results = milvus.search(
                collection_name=COLLECTION_NAME,
                data=[query_embedding],
                filter=search_filter,
                limit=input_data.top_k,
                output_fields=["content", "doc_id", "membro_id"],
                search_params={"metric_type": INDEX_METRIC, "params": {"nprobe": 16}},
            )
        except Exception as exc:
            log.error("knowledge_search.milvus_error", error=str(exc))
            return ToolOutput(success=False, result={"chunks": [], "message": f"Arama hatası: {exc}"})

        # ── 3. Sonuçları düzenle ─────────────────────────────────
        hits = results[0] if results else []
        chunks = []
        sources = []
        for hit in hits:
            entity = hit.get("entity", hit)  # farklı SDK sürümleri
            chunks.append(entity.get("content", ""))
            sources.append(entity.get("doc_id", ""))

        log.info(
            "knowledge_search.done",
            tenant_id=tenant_id,
            result_count=len(chunks),
        )

        return ToolOutput(
            success=True,
            result={
                "chunks":  chunks,
                "sources": sources,
                "count":   len(chunks),
            },
        )

    def schema(self) -> dict:
        base = super().schema()
        base["inputSchema"] = KnowledgeSearchInput.model_json_schema()
        return base


# Otomatik kayıt
knowledge_search = register_tool(KnowledgeSearchTool())

