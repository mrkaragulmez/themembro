# backend/app/core/config.py
# Faz 1 + Faz 2 — Uygulama konfigürasyonu (pydantic-settings ile .env okur)

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_domain: str = "localhost"
    frontend_url: str = "http://localhost:3000"

    # Veritabanı
    database_url: str = "postgresql+asyncpg://membro_user:membro_dev_pass@localhost:5432/membro_db"

    # JWT
    jwt_secret: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "35JWXFD3BwVF7ejTu8EcNmw"

    # Milvus
    milvus_uri: str = "http://localhost:19530"

    # ─── Faz 2: Cloudflare AI Gateway ─────────────────────────────────────
    cf_account_id: str = ""
    cf_gateway_id: str = "membro-gateway"
    # Gateway authentication token (cf-aig-authorization header)
    # Cloudflare Dashboard > AI Gateway > Settings > Auth Token
    cf_aig_token: str = ""

    @property
    def cf_ai_gateway_url(self) -> str:
        """Cloudflare AI Gateway base URL'ini hesaplar.

        Format: https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}
        """
        return (
            f"https://gateway.ai.cloudflare.com/v1"
            f"/{self.cf_account_id}/{self.cf_gateway_id}"
        )

    # ─── Faz 4: LiveKit WebRTC Ses Altyapısı ──────────────────────
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "devsecretkey-membro-local-dev001"

    @property
    def pg_checkpoint_url(self) -> str:
        """LangGraph PostgreSQL checkpointer için psycopg v3 uyumlu bağlantı URL'i.

        asyncpg driver prefix'i çıkarılır; psycopg standart postgresql:// şeması kullanır.
        """
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
