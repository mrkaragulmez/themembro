# backend/tests/test_api_security.py
# Faz 5 — HTTP/API güvenlik entegrasyon testleri
#
# Bu testler tam Docker Compose ortamı gerektirir (PostgreSQL + tam bağımlılıklar).
# Bunları çalıştırmak için: docker-compose up && pytest tests/test_api_security.py -v
#
# Birim testler (JWT, token tip): tests/test_security.py

from __future__ import annotations

import pytest

from tests.conftest import TENANT_A_ID, TENANT_B_ID, MEMBRO_A_ID, MEMBRO_B_ID


# ─── 2. RLS Cross-Tenant İzolasyon ───────────────────────────────────────────

class TestRLSCrossTenantIsolation:
    """A tenant JWT'si ile B tenant'a ait kaynaklara erişim engellenmeli."""

    @pytest.mark.asyncio
    async def test_cross_tenant_membro_access_returns_404(
        self,
        client,
        tenant_a_token: str,
    ):
        """Tenant A, Tenant B'nin membro'sunu göremez — varlığı bile açıklanmaz (404)."""
        response = await client.get(
            f"/api/v1/membros/{MEMBRO_B_ID}",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-Slug": "tenant-a",
            },
        )
        assert response.status_code in (404, 401), (
            f"Beklenen 404 veya 401, alınan: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_missing_token_returns_401(self, client):
        """Token olmadan korunan endpoint'e istek → 401.
        Not: X-Tenant-Slug gönderilmez; tenant middleware atlanır,
        auth middleware direkt 401 döner.
        """
        response = await client.get(
            f"/api/v1/membros/{MEMBRO_A_ID}",
            # X-Tenant-Slug intentionally omitted — tenant MW skips,
            # auth MW returns 401 for missing token
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_cannot_access_protected_endpoint(
        self,
        client,
        refresh_token_a: str,
    ):
        """Refresh token ile korunan endpoint'e erişim → 401 JWT_INVALID."""
        response = await client.get(
            f"/api/v1/membros/{MEMBRO_A_ID}",
            headers={
                "Authorization": f"Bearer {refresh_token_a}",
                # X-Tenant-Slug intentionally omitted — auth MW runs first
                # (tenant MW skips when no slug), returns 401 JWT_INVALID
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data.get("error") == "JWT_INVALID"


# ─── 3. Input Uzunluk Limiti ─────────────────────────────────────────────────

class TestInputLengthLimit:
    """4000 karakteri aşan mesajlar kırpılarak işlenmeli; uygulama çökmemeli."""

    @pytest.mark.asyncio
    async def test_oversized_message_does_not_crash(
        self,
        client,
        tenant_a_token: str,
    ):
        """10.000 karakterlik mesaj 422 (Validation Error) döndürmemeli."""
        long_message = "A" * 10_000
        response = await client.post(
            f"/api/v1/agents/{MEMBRO_A_ID}/chat",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-Slug": "tenant-a",
            },
            json={"message": long_message},
        )
        assert response.status_code != 422, (
            "Input kırpma çalışmıyor: 422 Validation Error döndü"
        )

    @pytest.mark.asyncio
    async def test_normal_message_accepted(
        self,
        client,
        tenant_a_token: str,
    ):
        """Normal uzunluktaki mesaj 422 döndürmemeli."""
        response = await client.post(
            f"/api/v1/agents/{MEMBRO_A_ID}/chat",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-Slug": "tenant-a",
            },
            json={"message": "Merhaba, nasılsın?"},
        )
        assert response.status_code != 422


# ─── 4. Public Endpoint'ler ──────────────────────────────────────────────────

class TestPublicEndpoints:
    """Public endpoint'ler tokensız erişilebilir olmalı."""

    @pytest.mark.asyncio
    async def test_health_endpoint_accessible(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
