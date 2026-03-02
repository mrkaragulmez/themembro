# backend/app/agents/tools/send_email.py
# Faz 2 — E-posta gönderme aracı (iskelet)
#
# Bu araç "action_agent" tarafından kullanılır.
# Gerçek e-posta entegrasyonu (Resend / SendGrid) sonraki sprintlerde eklenecek.

from __future__ import annotations

import structlog
from pydantic import Field, EmailStr

from app.agents.tools.base import BaseTool, ToolInput, ToolOutput, register_tool

log = structlog.get_logger()


class SendEmailInput(ToolInput):
    to: EmailStr = Field(..., description="Alıcı e-posta adresi")
    subject: str = Field(..., description="E-posta konusu")
    body: str = Field(..., description="E-posta gövdesi (düz metin veya HTML)")


class SendEmailTool(BaseTool):
    """Belirtilen adrese e-posta gönderir.

    Faz 2 sonunda Resend API ile entegre edilecek.
    """

    name = "send_email"
    description = (
        "Belirtilen e-posta adresine mesaj gönderir. "
        "Müşteriye bildirim, onay, rapor gibi durumlarda kullanılır."
    )

    async def run(self, arguments: dict) -> ToolOutput:  # type: ignore[override]
        input_data = SendEmailInput(**arguments)
        log.info(
            "send_email.run",
            tenant_id=input_data.tenant_id,
            to=input_data.to,
            subject=input_data.subject[:60],
        )
        # TODO: Resend API entegrasyonu
        return ToolOutput(
            success=True,
            result={"message": f"E-posta kuyruğa alındı → {input_data.to}"},
        )

    def schema(self) -> dict:
        base = super().schema()
        base["inputSchema"] = SendEmailInput.model_json_schema()
        return base


send_email = register_tool(SendEmailTool())
