# backend/app/core/exception_handler.py
# Faz 1 — Global exception handler; tüm yakalanmamış hataları MO_Eventlog'a yazar
# Her servis (FastAPI, LangGraph, Voice Worker) buradan türetilmiş handler kullanır

from __future__ import annotations

import traceback
import uuid

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

log = structlog.get_logger()


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Uygulama genelinde yakalanmamış tüm exception'ları karşılar.
    MO_Eventlog tablosuna yazar ve kullanıcıya request_id döner.
    """
    tenant_id   = getattr(request.state, "tenant_id",  None)
    user_id     = getattr(request.state, "user_id",    None)
    request_id  = getattr(request.state, "request_id", str(uuid.uuid4()))

    error_code  = type(exc).__name__
    error_msg   = str(exc)
    stack       = traceback.format_exc()

    # Structured log (stdout)
    log.error(
        "unhandled_exception",
        request_id=request_id,
        tenant_id=str(tenant_id) if tenant_id else None,
        code=error_code,
        message=error_msg,
        path=str(request.url),
    )

    # MO_Eventlog'a yaz (DB session varsa)
    db = getattr(request.state, "db", None)
    if db is not None:
        try:
            await db.execute(
                text("""
                    INSERT INTO "MO_Eventlog"
                        (tenant_id, user_id, service, level, code, message,
                         stack_trace, request_id, metadata)
                    VALUES
                        (:tenant_id, :user_id, 'api', 'ERROR', :code, :message,
                         :stack, :req_id, :meta::jsonb)
                """),
                {
                    "tenant_id": str(tenant_id) if tenant_id else None,
                    "user_id":   str(user_id) if user_id else None,
                    "code":      error_code,
                    "message":   error_msg,
                    "stack":     stack,
                    "req_id":    request_id,
                    "meta":      f'{{"path": "{request.url}", "method": "{request.method}"}}',
                },
            )
            await db.commit()
        except Exception:
            # Eventlog yazma bile başarısız olursa yutup devam et,
            # asıl hatayı kaybetme
            log.error("eventlog_write_failed", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error":      "internal_server_error",
            "request_id": request_id,
        },
    )
