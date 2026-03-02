# backend/app/core/security.py
# Faz 1 — JWT üretimi, doğrulama ve parola hashing

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Token Şemaları ────────────────────────────────────────────

class TokenPayload(BaseModel):
    sub: str          # user UUID
    tenant_id: str    # tenant UUID
    tenant_slug: str
    role: str         # tenant_admin | tenant_user | super_admin


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ─── Parola ────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── JWT ───────────────────────────────────────────────────────

def create_access_token(payload: TokenPayload) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_expire_minutes
    )
    data: dict[str, Any] = {
        **payload.model_dump(),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(payload: TokenPayload) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_expire_days
    )
    data: dict[str, Any] = {
        **payload.model_dump(),
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),  # Her token benzersiz — duplicate hash önler
    }
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Token'ı doğrular ve payload'ı döner. Geçersizse JWTError fırlatır."""
    raw = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    return TokenPayload(
        sub=raw["sub"],
        tenant_id=raw["tenant_id"],
        tenant_slug=raw["tenant_slug"],
        role=raw["role"],
    )
