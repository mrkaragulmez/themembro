# backend/app/middleware/auth.py
# Faz 1 — JWT doğrulama; token'ı Authorization header veya çerezden okur

import structlog
from fastapi import Request, Response
from jose import JWTError

from app.core.security import decode_token, decode_refresh_token

log = structlog.get_logger()

# Bu path'ler auth gerektirmez
PUBLIC_PATHS = {
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/register",
}

# Bu prefix'ler ile başlayan path'ler auth gerektirmez (GET-only sistem verileri)
PUBLIC_PREFIXES = (
    "/api/v1/sys-membros",
)


async def auth_middleware(request: Request, call_next) -> Response:
    """
    Her request başında JWT doğrular.
    Geçerli token varsa:
      - request.state.user_id
      - request.state.user_role
    set edilir.

    Token yoksa veya geçersizse public endpoint'lerde devam eder,
    korunan endpoint'lerde 401 döner.
    """
    request.state.user_id   = None
    request.state.user_role = None

    is_public = (
        request.url.path in PUBLIC_PATHS
        or request.url.path.startswith(PUBLIC_PREFIXES)
    )

    # Token'ı çöz: önce Authorization header, sonra cookie
    token: str | None = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
    elif "access_token" in request.cookies:
        token = request.cookies["access_token"]

    if token:
        try:
            # Refresh endpoint yalnızca refresh token kabul eder; diğerleri access token bekler
            is_refresh_path = request.url.path == "/api/v1/auth/refresh"
            payload = (
                decode_refresh_token(token)
                if is_refresh_path
                else decode_token(token, expected_type="access")
            )
            request.state.user_id   = payload.sub
            request.state.user_role = payload.role
            # tenant_id JWT'den de gelebilir; middleware zaten header'dan set etti,
            # ama JWT değeriyle çelişiyorsa JWT kazanır (RLS güvenliği)
            if payload.tenant_id:
                request.state.tenant_id = payload.tenant_id
        except JWTError as e:
            log.warning("jwt_invalid", error=str(e), path=request.url.path)
            if not is_public:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={"error": "JWT_INVALID"},
                )
    elif not is_public:
        # Korunan endpoint'e token'sız erişim
        if request.url.path.startswith("/api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"error": "authentication_required"},
            )

    return await call_next(request)
