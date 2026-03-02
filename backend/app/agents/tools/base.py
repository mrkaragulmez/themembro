# backend/app/agents/tools/base.py
# Faz 2 — Temel araç (tool) sözleşmesi ve kayıt sistemi
#
# LangChain'in @tool dekoratörü yerine saf Pydantic + async fonksiyon
# kullanılır; MCP sunucusuyla uyumlu kalmak için.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class ToolInput(BaseModel):
    """Tüm araç girdilerinin temel şeması."""
    tenant_id: str
    membro_id: str | None = None


class ToolOutput(BaseModel):
    """Tüm araç çıktılarının temel şeması."""
    success: bool
    result: Any = None
    error: str | None = None


class BaseTool(ABC):
    """Membro araç arayüzü.

    Her araç bu sınıfı miras alır. ``run`` ham argüman sözlüğü alır;
    her alt-sınıf kendi input şemasını içinde parse eder.
    """

    name: str
    description: str

    @abstractmethod
    async def run(self, arguments: dict) -> ToolOutput:
        """Aracı çalıştırır. arguments: MCP'den gelen ham dict."""
        ...

    def schema(self) -> dict[str, Any]:
        """MCP tool tanımı formatında JSON şemasını döndürür."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": ToolInput.model_json_schema(),
        }


# ─── Araç Kayıt Defteri ─────────────────────────────────────────────────────

_REGISTRY: dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> BaseTool:
    """Aracı global kayıt defterine ekler."""
    _REGISTRY[tool.name] = tool
    return tool


def get_tool(name: str) -> BaseTool | None:
    return _REGISTRY.get(name)


def list_tools() -> list[dict]:
    """Tüm kayıtlı araçların MCP şemalarını döndürür."""
    return [t.schema() for t in _REGISTRY.values()]
