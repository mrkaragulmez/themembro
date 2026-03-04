# backend/app/api/v1/auth.py
# Faz 1 — Auth endpoint'leri: login, refresh, logout, register

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    TokenPair,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.db.session import get_db
from app.db.models import Tenant, User, RefreshToken

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Şemalar ────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str          # Hangi tenant'a kayıt olunuyor
    full_name: str | None = None

class RefreshRequest(BaseModel):
    refresh_token: str


# ─── Yardımcı ────────────────────────────────────────────────────

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_token_pair(user: User, tenant: Tenant) -> TokenPair:
    payload = TokenPayload(
        sub=str(user.id),
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug,
        role=user.role,
    )
    access  = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return TokenPair(access_token=access, refresh_token=refresh)


def _set_cookies(response: Response, pair: TokenPair, domain: str):
    secure = settings.app_env != "development"
    opts = dict(httponly=True, secure=secure, samesite="lax", domain=domain)
    response.set_cookie("access_token",  pair.access_token,  max_age=settings.jwt_access_expire_minutes * 60, **opts)
    response.set_cookie("refresh_token", pair.refresh_token, max_age=settings.jwt_refresh_expire_days * 86400, **opts)


# ─── Register ────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # Tenant bul
    tenant = (await db.execute(
        select(Tenant).where(Tenant.slug == body.tenant_slug, Tenant.is_active.is_(True))
    )).scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="tenant_not_found")

    # E-posta bu tenant'ta zaten var mı?
    existing = (await db.execute(
        select(User).where(User.email == body.email, User.tenant_id == tenant.id)
    )).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="email_already_registered")

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="member",
    )
    db.add(user)
    await db.flush()  # id'yi al

    pair = _make_token_pair(user, tenant)

    # Refresh token'ı kaydet
    rt = RefreshToken(
        tenant_id=tenant.id,
        user_id=user.id,
        token_hash=_token_hash(pair.refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days),
    )
    db.add(rt)

    _set_cookies(response, pair, settings.app_domain)
    return {
        "message": "registered",
        "user_id": str(user.id),
        "access_token": pair.access_token,
        "token_type": "bearer",
    }


# ─── Login ───────────────────────────────────────────────────────

@router.post("/login")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = request.state.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_context_required")

    user = (await db.execute(
        select(User).where(User.email == body.email, User.tenant_id == tenant_id)
    )).scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="account_disabled")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    pair   = _make_token_pair(user, tenant)

    rt = RefreshToken(
        tenant_id=tenant.id,
        user_id=user.id,
        token_hash=_token_hash(pair.refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days),
    )
    db.add(rt)

    _set_cookies(response, pair, settings.app_domain)
    return {
        "message": "ok",
        "role": user.role,
        "access_token": pair.access_token,
        "token_type": "bearer",
    }


# ─── Refresh ──────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token(
    body: RefreshRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import decode_token
    from jose import JWTError

    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")

    th = _token_hash(body.refresh_token)
    rt = (await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == th,
            RefreshToken.revoked.is_(False),
        )
    )).scalar_one_or_none()

    if not rt or rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="refresh_token_expired_or_revoked")

    # Eski token'ı iptal et (rotation)
    rt.revoked = True

    user   = (await db.execute(select(User).where(User.id == rt.user_id))).scalar_one()
    tenant = (await db.execute(select(Tenant).where(Tenant.id == rt.tenant_id))).scalar_one()
    pair   = _make_token_pair(user, tenant)

    new_rt = RefreshToken(
        tenant_id=tenant.id,
        user_id=user.id,
        token_hash=_token_hash(pair.refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days),
    )
    db.add(new_rt)

    _set_cookies(response, pair, settings.app_domain)
    return {"message": "ok"}


# ─── Logout ───────────────────────────────────────────────────

@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh = request.cookies.get("refresh_token")
    if refresh:
        th = _token_hash(refresh)
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == th)
            .values(revoked=True)
        )

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "logged_out"}
