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

    while True:
        line = await asyncio.to_thread(sys.stdin.readline)
        if not line:
            break

        line = line.strip()
        if not line:
            continue

        try:
            req_data = json.loads(line)
            response = await protocol_handler.handle_request(req_data)
            if response is not None:
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
