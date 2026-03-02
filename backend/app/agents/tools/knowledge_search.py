# backend/app/agents/tools/knowledge_search.py
# Faz 2 — Bilgi bankası arama aracı (iskelet)
#
# Faz 3'te Milvus (vektör) + Neo4j (graf) entegrasyonu eklenecek.
# Şu an placeholder implementasyon döndürür.

from __future__ import annotations

import structlog
from pydantic import Field

from app.agents.tools.base import BaseTool, ToolInput, ToolOutput, register_tool

log = structlog.get_logger()


class KnowledgeSearchInput(ToolInput):
    query: str = Field(..., description="Aranacak metin sorgusu")
    top_k: int = Field(default=5, description="Döndürülecek maksimum sonuç sayısı")


class KnowledgeSearchTool(BaseTool):
    """Bilgi bankasını vektör benzerliği ile arar.

    Faz 3'te Milvus + Neo4j pipeline'ına bağlanacak.
    """

    name = "search_knowledge_base"
    description = (
        "Membro'nun bilgi bankasında semantik arama yapar. "
        "Şirket politikaları, ürün bilgileri, sıkça sorulan sorular gibi "
        "yapılandırılmış verilere erişmek için kullanılır."
    )

    async def run(self, arguments: dict) -> ToolOutput:  # type: ignore[override]
        input_data = KnowledgeSearchInput(**arguments)
        log.info(
            "knowledge_search.run",
            tenant_id=input_data.tenant_id,
            query=input_data.query[:80],
        )
        # TODO (Faz 3): Milvus'a bağlan, embedding al, top_k döndür
        return ToolOutput(
            success=True,
            result={
                "chunks": [],
                "message": "Faz 3'te Milvus entegrasyonu ile dolacak.",
            },
        )

    def schema(self) -> dict:
        base = super().schema()
        base["inputSchema"] = KnowledgeSearchInput.model_json_schema()
        return base


# Otomatik kayıt
knowledge_search = register_tool(KnowledgeSearchTool())
