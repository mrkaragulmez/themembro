## backend/tests/conftest.py
# Faz 5 — Pytest global fixture'ları
#
# İki farklı tenant için JWT token üretici, async HTTP test client ve
# test environment ayarlarını içerir.
#
# Tasarım notu: `app` import'u lazy — fixture içinde yapılır.
# Bu sayede birim testleri (token, güvenlik) LangGraph/Milvus/Neo4j
# bağımlılıkları kurulu olmasa da çalışır.

from __future__ import annotations

import os
import uuid
import pytest
import pytest_asyncio
from pathlib import Path
from typing import AsyncGenerator

# Proje kökündeki .env dosyasını yükle (eğer mevcutsa) — böylece şifreler
# conftest setdefault çağrılarından önce env'e girer.
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)  # shell env varsa korur, yoksa .env'den yükler
except ImportError:
    pass  # python-dotenv yoksa sorun değil, ortam değişkenleri zaten mevcutsa kullanılır

# Test ortamı ayarları — gerçek dış servislere bağlanmayı engelle
os.environ.setdefault("APP_ENV", "test")
# DATABASE_URL: .env'den yüklendi; yoksa lokale güvenli fallback (CI için)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://membro_user:membro_dev_pass@localhost:5432/membro_db")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-do-not-use-in-prod")
os.environ.setdefault("CF_AIG_TOKEN", "test-token")
os.environ.setdefault("CF_ACCOUNT_ID", "test-account")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from app.core.security import create_access_token, create_refresh_token, TokenPayload


# ─── Tenant / Kullanıcı Sabitleri ────────────────────────────────────────────

TENANT_A_ID   = str(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
TENANT_B_ID   = str(uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
USER_A_ID     = str(uuid.UUID("a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1"))
USER_B_ID     = str(uuid.UUID("b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1"))
MEMBRO_A_ID   = str(uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"))
MEMBRO_B_ID   = str(uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"))


# ─── Token Fixture'ları ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def tenant_a_token() -> str:
    """Tenant A için geçerli access token."""
    payload = TokenPayload(
        sub=USER_A_ID,
        tenant_id=TENANT_A_ID,
        tenant_slug="tenant-a",
        role="tenant_admin",
    )
    return create_access_token(payload)


@pytest.fixture(scope="session")
def tenant_b_token() -> str:
    """Tenant B için geçerli access token."""
    payload = TokenPayload(
        sub=USER_B_ID,
        tenant_id=TENANT_B_ID,
        tenant_slug="tenant-b",
        role="tenant_admin",
    )
    return create_access_token(payload)


@pytest.fixture(scope="session")
def refresh_token_a() -> str:
    """Tenant A için refresh token (API erişimine KULLANILMAMALI)."""
    payload = TokenPayload(
        sub=USER_A_ID,
        tenant_id=TENANT_A_ID,
        tenant_slug="tenant-a",
        role="tenant_admin",
    )
    return create_refresh_token(payload)


# ─── HTTP Client (Lazy App Import) ───────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator:
    """Async test HTTP client — gerçek bir sunucu başlatmaz, ASGI doğrudan çağırılır.

    app import'u burada yapılır (lazy); birim testleri bu fixture'ı kullanmadığı
    sürece heavy bağımlılıklar yüklenmez.
    """
    from httpx import AsyncClient, ASGITransport
    from app.main import app  # lazy import

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

