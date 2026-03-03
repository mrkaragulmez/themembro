# backend/app/voice/worker.py
# Faz 4 — LiveKit Voice Worker Giriş Noktası
#
# Bu modül doğrudan Python subprocess olarak çalışır:
#     python -m app.voice.worker
#
# Başladığında LiveKit Server'a bağlanır ve "membro-voice-agent" adıyla
# agent job kuyruğunu dinlemeye başlar. POST /meetings/ endpoint'i
# yeni bir toplantı oluşturduğunda bu worker'a dispatch yapılır.

from __future__ import annotations

import os
import sys
import logging
import structlog

log = structlog.get_logger()


def main() -> None:
    """Worker ana döngüsünü başlatır."""

    # livekit-agents yüklü mü?
    try:
        from livekit.agents import WorkerOptions, cli  # type: ignore
    except ImportError:
        log.error(
            "livekit_agents_paketi_bulunamadi — "
            "'pip install livekit-agents livekit-plugins-openai livekit-plugins-silero' komutunu çalıştırın."
        )
        sys.exit(1)

    from app.voice.agent import entrypoint  # geç import (circular önlemi)
    from app.core.config import settings    # .env değerlerini oku

    # LiveKit bağlantı bilgilerini ortam değişkenine yaz (SDK kendi okur)
    os.environ.setdefault("LIVEKIT_URL",        settings.livekit_url)
    os.environ.setdefault("LIVEKIT_API_KEY",    settings.livekit_api_key)
    os.environ.setdefault("LIVEKIT_API_SECRET", settings.livekit_api_secret)

    log.info(
        "voice_worker_starting — url=%s agent=%s",
        settings.livekit_url,
        "membro-voice-agent",
    )

    # WorkerOptions ile agent'ı kaydet ve job kuyruğunu dinle
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="membro-voice-agent",  # dispatch API'de kullanılan isim
        )
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    main()
