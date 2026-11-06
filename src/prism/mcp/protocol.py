"""Model Context Protocol (MCP) JSON-RPC 2.0 protocol layer (Phase 24).

Implements standard MCP protocol methods (initialize, ping, tools/list, tools/call)
conforming to the official Model Context Protocol specifications.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from prism.logging.logger import get_logger
from prism.mcp.service import MCPService, MCPToolDefinition

logger = get_logger(__name__)

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "prism-mcp-server"
SERVER_VERSION = "0.1.0"


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any | None = None
    error: dict[str, Any] | None = None


class MCPProtocolHandler:
    """Standard JSON-RPC 2.0 protocol dispatcher for the PRISM MCP Server."""

    def __init__(self, mcp_service: MCPService) -> None:
        self.mcp_service = mcp_service

    def _convert_tool_to_json_schema(self, tool: MCPToolDefinition) -> dict[str, Any]:
        """Convert PRISM tool definition into standard JSON Schema for MCP tools/list."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for p in tool.parameters:
            properties[p.name] = {
                "type": p.type,
                "description": p.description,
            }
            if p.required:
                required.append(p.name)

        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    async def handle_request(
        self,
        request_dict: dict[str, Any],
        caller_id: str | None = None,
    ) -> dict[str, Any]:
        """Process a standard MCP JSON-RPC 2.0 request and return a standard response."""
        req_id = request_dict.get("id")
        method = request_dict.get("method")
        params = request_dict.get("params") or {}

        if not method or not isinstance(method, str):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: method is required",
                },
            }

        try:
            # 1. MCP initialize handshake
            if method == "initialize":
                client_version = params.get("protocolVersion", MCP_PROTOCOL_VERSION)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": client_version,
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "logging": {},
                        },
                        "serverInfo": {
                            "name": SERVER_NAME,
                            "version": SERVER_VERSION,
                        },
                    },
                }

            # 2. MCP initialized notification
            if method == "notifications/initialized":
                logger.info("MCP client handshake initialized successfully")
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}

            # 3. MCP ping
            if method == "ping":
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}

            # 4. MCP tools/list
            if method == "tools/list":
                tools = self.mcp_service.list_tools()
                formatted_tools = [self._convert_tool_to_json_schema(t) for t in tools]
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": formatted_tools},
                }

            # 5. MCP tools/call
            if method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments") or {}

                if not tool_name or not isinstance(tool_name, str):
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32602,
                            "message": "Invalid params: 'name' is required for tools/call",
                        },
                    }

                exec_result = await self.mcp_service.execute_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    caller_id=caller_id,
                )

                if exec_result.status == "success":
                    text_content = (
                        json.dumps(exec_result.data, default=str)
                        if not isinstance(exec_result.data, str)
                        else exec_result.data
                    )
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": text_content}],
                            "isError": False,
                        },
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": exec_result.error
                                    or "Tool execution failed",
                                }
                            ],
                            "isError": True,
                        },
                    }

            # Method not recognized
            logger.warning("Unrecognized MCP method requested: %s", method)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found or unsupported",
                },
            }

        except Exception as e:
            logger.exception("Error handling MCP JSON-RPC method '%s'", method)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal JSON-RPC error: {e}"},
            }
