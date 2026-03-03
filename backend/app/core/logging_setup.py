# backend/app/core/logging_setup.py
# Faz 5 — Structured logging konfigürasyonu
#
# configure_logging() uygulama başında bir kez çağrılır (bkz. main.py lifespan).
# Geliştirme ortamında renkli console çıktısı, üretimde JSON formatı kullanılır.
# Her log kaydına otomatik timestamp, log level ve tenant_id bağlamı eklenir.

import logging
import sys

import structlog
from structlog.types import Processor

from app.core.config import settings


def configure_logging() -> None:
    """structlog işlemci zincirini ve Python logging entegrasyonunu kurar.

    Geliştirme:  renkli console (dev deneyimi için)
    Üretim:      JSON Lines (log aggregatör için)
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.app_env == "production":
        # Üretim: JSON Lines — Datadog / Loki / CloudWatch uyumlu
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        # Geliştirme: renkli, okunabilir çıktı
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(
        logging.DEBUG if settings.app_env != "production" else logging.INFO
    )

    # 3. parti kütüphanelerin aşırı verbose loglarını sustur
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
