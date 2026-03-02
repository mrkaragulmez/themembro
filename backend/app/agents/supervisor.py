# backend/app/agents/supervisor.py
# Faz 2 — LangGraph Supervisor + alt-ajan grafikleri
#
# Supervisor asla doğrudan içerik üretmez; Pydantic Structured Output
# ile hangi ajanın devreye gireceğine karar verir.
# Grafiğin tek giriş noktası: compile_graph() fonksiyonu.

from __future__ import annotations

import structlog
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from app.agents.state import MembroState, AgentName
from app.core.config import settings

log = structlog.get_logger()

# ─── Supervisor Karar Modeli ────────────────────────────────────────────────

class SupervisorDecision(BaseModel):
    """Supervisor'ın Structured Output formatı.

    next: Hangi alt-ajan devam edecek ya da konuşma bitiyor.
    reasoning: İnsan-okunabilir karar gerekçesi (loglama için).
    """
    next: AgentName
    reasoning: str


# ─── LLM ────────────────────────────────────────────────────────────────────
# Not: Cloudflare AI Gateway üzerinden OpenAI'ye yönlendirilir.
# base_url, özel CF gateway URL'sidir.

def _make_llm() -> ChatOpenAI:
    """CF Unified Billing: CF AIG Token doğrudan openai_api_key olarak geçilir.
    ChatOpenAI SDK bunu Authorization: Bearer {token} olarak gönderir;
    CF Gateway bu header'ı kendi auth'u olarak kabul eder, provider key vault'tan alır.
    """
    gateway_url = f"{settings.cf_ai_gateway_url.rstrip('/')}/openai"
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.cf_aig_token,
        openai_api_base=gateway_url,
    ).with_structured_output(SupervisorDecision)


# ─── Supervisor Node ────────────────────────────────────────────────────────

SUPERVISOR_SYSTEM_PROMPT = """Sen bir Membro AI Supervisor'ısın.
Kullanıcı mesajını analiz et ve hangi alt-ajanın devreye gireceğine karar ver:

- knowledge_agent : Soru sormak, bilgi almak, selamlaşmak veya genel konuşmak için
- action_agent    : Dışarıya yazma, e-posta, CRM gibi somut bir eylem gerekiyorsa

KURAL: Her zaman bir ajan seç. Asla __end__ seçme — yanıt üretmeden konuşmayı bitirme.
Şüphe durumunda knowledge_agent seç.

Sadece JSON formatında yanıt ver. Yorum ekleme."""


async def supervisor_node(state: MembroState) -> dict:
    """Supervisor düğümü: hangi ajan devreye girecek karar verir."""
    log.info(
        "supervisor.decision",
        tenant_id=state.tenant_id,
        membro_id=state.membro_id,
        turn=state.turn_count,
    )

    llm = _make_llm()
    decision: SupervisorDecision = await llm.ainvoke(
        [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            *state.messages,
        ]
    )

    log.info(
        "supervisor.decided",
        next_agent=decision.next,
        reasoning=decision.reasoning,
    )

    return {
        "next_agent": decision.next,
        "turn_count": state.turn_count + 1,
    }


# ─── Knowledge Agent Node ───────────────────────────────────────────────────

KNOWLEDGE_AGENT_SYSTEM = """Sen bir bilgi bankası ajanısın.
Verilen bağlamı kullanarak kullanıcıya doğru ve öz yanıtlar ver.
Bilmediğin bir şey varsa açıkça belirt."""


async def knowledge_agent_node(state: MembroState) -> dict:
    """Bilgi bankası ajanı: retrieval context'i kullanarak yanıt üretir."""
    log.info("knowledge_agent.start", membro_id=state.membro_id)

    gateway_url = f"{settings.cf_ai_gateway_url.rstrip('/')}/openai"
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        openai_api_key=settings.cf_aig_token,
        openai_api_base=gateway_url,
        default_headers={
            "cf-aig-metadata": f'{{"tenant_id": "{state.tenant_id}", "membro_id": "{state.membro_id}"}}',
        },
    )

    # Retrieval context varsa sisteme ekle (Faz 3'te Milvus'tan gelecek)
    system_content = KNOWLEDGE_AGENT_SYSTEM
    if state.retrieval_context.chunks:
        context_text = "\n\n".join(state.retrieval_context.chunks)
        system_content += f"\n\n## Bilgi Bankası Bağlamı\n{context_text}"

    response = await llm.ainvoke(
        [SystemMessage(content=system_content), *state.messages]
    )

    return {"messages": [response], "next_agent": "__end__"}


# ─── Action Agent Node ──────────────────────────────────────────────────────

ACTION_AGENT_SYSTEM = """Sen bir eylem ajanısın.
Kullanıcının isteğini yerine getirmek için mevcut araçları (tools) kullanabilirsin.
Her eylem öncesinde kısa bir onay mesajı yaz."""


async def action_agent_node(state: MembroState) -> dict:
    """Eylem ajanı: MCP araçları aracılığıyla dışarıya yazma işlemleri yapar."""
    log.info("action_agent.start", membro_id=state.membro_id)

    gateway_url = f"{settings.cf_ai_gateway_url.rstrip('/')}/openai"
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.cf_aig_token,
        openai_api_base=gateway_url,
    )

    response = await llm.ainvoke(
        [SystemMessage(content=ACTION_AGENT_SYSTEM), *state.messages]
    )

    return {"messages": [response], "next_agent": "__end__"}


# ─── Yönlendirme Fonksiyonu ─────────────────────────────────────────────────

def route_after_supervisor(state: MembroState) -> AgentName:
    """Supervisor kararına göre sonraki düğümü döndürür."""
    if state.next_agent == "__end__" or state.next_agent is None:
        return END  # type: ignore[return-value]
    if state.turn_count >= 15:
        # recursion_limit güvencesi
        log.warning("supervisor.recursion_limit_reached", turn=state.turn_count)
        return END  # type: ignore[return-value]
    return state.next_agent  # type: ignore[return-value]


# ─── Graf Derleme ───────────────────────────────────────────────────────────

def compile_graph(checkpointer=None):
    """LangGraph grafını derler ve döndürür.

    checkpointer=None → geliştirme modunda in-memory; üretimde
    PostgreSQL checkpointer (langgraph-checkpoint-postgres) geçilir.
    """
    builder = StateGraph(MembroState)

    # Düğümler
    builder.add_node("supervisor",       supervisor_node)
    builder.add_node("knowledge_agent",  knowledge_agent_node)
    builder.add_node("action_agent",     action_agent_node)

    # Kenarlar
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "knowledge_agent": "knowledge_agent",
            "action_agent":    "action_agent",
            END:               END,
        },
    )
    builder.add_edge("knowledge_agent", END)
    builder.add_edge("action_agent",    END)

    # Checkpoint
    cp = checkpointer or MemorySaver()
    return builder.compile(checkpointer=cp)
