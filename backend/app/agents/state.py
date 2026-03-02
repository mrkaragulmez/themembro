# backend/app/agents/state.py
# Faz 2 — LangGraph durum (state) tanımları
#
# MembroState: Supervisor ve tüm alt-ajanların paylaştığı grafiğin
# tek kaynaklı-doğru (single source of truth) durum şeması.

from __future__ import annotations

from typing import Annotated, Literal
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# ─── Mevcut Ajan Tanımları ──────────────────────────────────────────────────
# Aktif membrolara göre genişler; şimdilik sabit Literal kullanıyoruz.
# Dinamik ajan kaydı Faz 2 ilerleyen aşamalarında veritabanından beslenecek.

AgentName = Literal["supervisor", "knowledge_agent", "action_agent", "__end__"]


# ─── Retrieval Bağlamı ──────────────────────────────────────────────────────

class RetrievalContext(BaseModel):
    """Bilgi bankasından getirilen snippet'lar (Faz 3'te dolacak)."""
    chunks: list[str] = Field(default_factory=list)
    graph_facts: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


# ─── Ana Durum ──────────────────────────────────────────────────────────────

class MembroState(BaseModel):
    """Tüm grafik boyunca akan merkezi durum objesi.

    ``messages`` alanı LangGraph'ın ``add_messages`` reducer'ı ile
    otomatik olarak birleştirilir (mevcut liste üzerine append, fazlası değil).
    """

    # Konuşma geçmişi — LangGraph reducer ile yönetilir
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    # Tenant ve kimlik bilgileri — her pakette zorunlu
    tenant_id: str
    membro_id: str
    conversation_id: str

    # Supervisor kararı: bir sonraki hangi ajan çalışacak
    next_agent: AgentName | None = None

    # Retrieval pipeline'dan gelen bağlam (Faz 3'te doldurulur)
    retrieval_context: RetrievalContext = Field(default_factory=RetrievalContext)

    # Güvenlik ve izleme
    turn_count: int = 0
    is_interrupted: bool = False  # interrupt_before ile durduruldu mu

    # Hata durumu
    error: str | None = None

    class Config:
        arbitrary_types_allowed = True  # BaseMessage için gerekli
