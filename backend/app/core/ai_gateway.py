# backend/app/core/ai_gateway.py
# Faz 2 — Cloudflare AI Gateway proxy katmanı
# Tüm LLM çağrıları bu modül üzerinden geçer; hiçbir bileşen doğrudan
# provider endpoint'lerine ulaşamaz.

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger()

# ─── Sabitler ──────────────────────────────────────────────────────────────

_OPENAI_PROVIDER    = "openai"
_ANTHROPIC_PROVIDER = "anthropic"
_GROQ_PROVIDER      = "groq"


def _gateway_url(provider: str, path: str) -> str:
    """Cloudflare AI Gateway base URL'ini döndürür.

    Format: https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/{provider}/{path}
    """
    base = settings.cf_ai_gateway_url.rstrip("/")
    return f"{base}/{provider}/{path.lstrip('/')}"


def _build_headers(
    *,
    provider: str,
    tenant_id: str,
    membro_id: str | None = None,
    conversation_id: str | None = None,
    cache_ttl: int | None = None,
) -> dict[str, str]:
    """Gateway + provider header'larını birleştirir."""
    metadata: dict[str, str] = {"tenant_id": tenant_id}
    if membro_id:
        metadata["membro_id"] = membro_id
    if conversation_id:
        metadata["conversation_id"] = conversation_id

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "cf-aig-metadata": json.dumps(metadata),
    }

    # Cloudflare Unified Billing / BYOK: provider API anahtarları CF vault'unda
    # saklanır. Bizden beklenen tek auth cf-aig-authorization header'ıdır.
    if settings.cf_aig_token:
        headers["cf-aig-authorization"] = f"Bearer {settings.cf_aig_token}"

    if cache_ttl is not None:
        headers["cf-aig-cache-ttl"] = str(cache_ttl)

    # Anthropic API sürüm header'ı — key değil, sadece protokol versiyonu
    if provider == _ANTHROPIC_PROVIDER:
        headers["anthropic-version"] = "2023-06-01"

    return headers


# ─── Ana sınıf ──────────────────────────────────────────────────────────────


class AIGateway:
    """Cloudflare AI Gateway üzerinden LLM çağrısı yapan async istemci.

    Kullanım::

        gw = AIGateway()
        response = await gw.chat(
            provider="openai",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Merhaba"}],
            tenant_id="tenant-uuid",
        )
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)

    # ─── Chat Completions (non-streaming) ──────────────────────

    async def chat(
        self,
        *,
        provider: str = _OPENAI_PROVIDER,
        model: str = "gpt-4o-mini",
        messages: list[dict[str, str]],
        tenant_id: str,
        membro_id: str | None = None,
        conversation_id: str | None = None,
        cache_ttl: int | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        extra_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Tek seferlik chat completion isteği atar ve dict olarak döndürür."""
        url = _gateway_url(provider, "chat/completions")
        headers = _build_headers(
            provider=provider,
            tenant_id=tenant_id,
            membro_id=membro_id,
            conversation_id=conversation_id,
            cache_ttl=cache_ttl,
        )
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra_body:
            payload.update(extra_body)

        log.info(
            "ai_gateway.chat",
            provider=provider,
            model=model,
            tenant_id=tenant_id,
            membro_id=membro_id,
        )

        resp = await self._client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    # ─── Chat Completions (streaming) ──────────────────────────

    async def chat_stream(
        self,
        *,
        provider: str = _OPENAI_PROVIDER,
        model: str = "gpt-4o-mini",
        messages: list[dict[str, str]],
        tenant_id: str,
        membro_id: str | None = None,
        conversation_id: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Chat completion isteğini SSE stream olarak döndürür.

        Her yield, ham SSE satırıdır (``data: {...}`` formatında).
        """
        url = _gateway_url(provider, "chat/completions")
        headers = _build_headers(
            provider=provider,
            tenant_id=tenant_id,
            membro_id=membro_id,
            conversation_id=conversation_id,
        )
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        log.info(
            "ai_gateway.chat_stream",
            provider=provider,
            model=model,
            tenant_id=tenant_id,
            membro_id=membro_id,
        )

        async with self._client.stream(
            "POST", url, headers=headers, json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    yield line

    # ─── Embeddings ────────────────────────────────────────────

    async def embeddings(
        self,
        *,
        provider: str = _OPENAI_PROVIDER,
        model: str = "text-embedding-3-small",
        input: str | list[str],
        tenant_id: str,
    ) -> list[list[float]]:
        """Embedding vektörlerini döndürür (Faz 3 RAG pipeline için)."""
        url = _gateway_url(provider, "embeddings")
        headers = _build_headers(provider=provider, tenant_id=tenant_id)
        payload = {"model": model, "input": input}

        resp = await self._client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]

    # ─── Lifecycle ─────────────────────────────────────────────

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AIGateway":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()


# ─── Singleton (dependency injection için) ─────────────────────────────────

_gateway: AIGateway | None = None


def get_gateway() -> AIGateway:
    """FastAPI Depends() ile kullanılacak singleton döndürür."""
    global _gateway
    if _gateway is None:
        _gateway = AIGateway()
    return _gateway
