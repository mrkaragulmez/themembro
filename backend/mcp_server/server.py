# backend/mcp_server/server.py
# Faz 2 — Membro Internal MCP Sunucusu
#
# Model Context Protocol (spec 2025-11-05) üzerinden Membro'nun dahili
# araçlarını dış istemcilere ve ajan sistemine açar.
# Protokol: HTTP + SSE (stateless remote server).
#
# Çalıştırmak için:
#   python -m mcp_server.server
# Ya da FastAPI'ye mount etmek için mcp_app() kullanılır.

from __future__ import annotations

import json
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# Araçları import et (register_tool çağrısını tetikler)
import app.agents.tools.knowledge_search  # noqa: F401
import app.agents.tools.send_email        # noqa: F401

from app.agents.tools.base import list_tools, get_tool

log = structlog.get_logger()


# ─── Request/Response Şemaları (modül seviyesinde — Pydantic için zorunlu) ──

class CallToolRequest(BaseModel):
    name: str
    arguments: dict


# ─── MCP App ────────────────────────────────────────────────────────────────

def create_mcp_app() -> FastAPI:
    """Bağımsız mount edilebilir bir FastAPI sub-application döndürür.

    Ana uygulamaya şöyle mount edilir::

        app.mount("/mcp", create_mcp_app())
    """
    mcp = FastAPI(
        title="Membro MCP Server",
        description="Model Context Protocol — Membro Internal Tools",
        version="1.0.0",
    )

    # ─── MCP: initialize ────────────────────────────────────────

    @mcp.post("/initialize")
    async def initialize():
        """MCP handshake — sunucu yeteneklerini bildirir."""
        return {
            "protocolVersion": "2025-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {},
                "prompts": {},
            },
            "serverInfo": {
                "name": "membro-mcp-server",
                "version": "1.0.0",
            },
        }

    # ─── MCP: tools/list ────────────────────────────────────────

    @mcp.post("/tools/list")
    async def tools_list():
        """Kayıtlı tüm araçların şemalarını döndürür."""
        return {"tools": list_tools()}

    # ─── MCP: tools/call ────────────────────────────────────────

    @mcp.post("/tools/call")
    async def tools_call(req: CallToolRequest):
        """Belirtilen aracı çalıştırır ve sonucu döndürür."""
        tool = get_tool(req.name)
        if tool is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"Tool '{req.name}' bulunamadı."},
            )

        log.info("mcp.tools_call", tool=req.name, args=req.arguments)

        try:
            output = await tool.run(req.arguments)
        except Exception as exc:
            return JSONResponse(
                status_code=422,
                content={"error": f"Araç çalıştırma hatası: {exc}"},
            )
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(output.model_dump(), ensure_ascii=False),
                }
            ],
            "isError": not output.success,
        }

    # ─── SSE Event Stream (MCP Streamable HTTP) ─────────────────

    @mcp.get("/sse")
    async def sse_stream(request: Request):
        """MCP Streamable HTTP transport için SSE endpoint'i."""

        async def event_generator():
            yield "event: connected\ndata: {}\n\n"
            # TODO: Gelecekte notification push desteği eklenecek
            # Şimdilik sadece bağlantı onayı gönderilir
            if await request.is_disconnected():
                return

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return mcp
