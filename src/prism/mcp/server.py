"""Model Context Protocol (MCP) Standard Stdio Server (Phase 24).

Allows any standard MCP client or external AI tool (e.g., Claude Desktop,
Cursor, Antigravity) to communicate with PRISM via stdin/stdout line-delimited JSON-RPC.
"""

from __future__ import annotations

import asyncio
import json
import sys

from prism.api.dependencies import mcp_service
from prism.logging.logger import get_logger
from prism.mcp.protocol import MCPProtocolHandler

logger = get_logger(__name__)


async def run_stdio_server() -> None:
    """Run standard line-delimited JSON-RPC 2.0 loop over stdin/stdout."""
    protocol_handler = MCPProtocolHandler(mcp_service)
    loop = asyncio.get_running_loop()

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line_bytes = await reader.readline()
        if not line_bytes:
            break

        line = line_bytes.decode("utf-8").strip()
        if not line:
            continue

        try:
            req_data = json.loads(line)
            response = await protocol_handler.handle_request(req_data)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError as err:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {err}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
        except Exception as err:
            logger.exception("Fatal error in MCP stdio server")
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal error: {err}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


def main() -> None:
    """CLI entrypoint for running the PRISM MCP server."""
    asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
