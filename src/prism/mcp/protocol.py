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
SUPPORTED_PROTOCOL_VERSIONS: frozenset[str] = frozenset({"2024-11-05"})
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
    ) -> dict[str, Any] | None:
        """Process a standard MCP JSON-RPC 2.0 request or notification.

        Returns a JSON-RPC response dictionary for normal requests, or None
        if the incoming message is a valid JSON-RPC 2.0 notification (omitted ID).
        """
        req_id = request_dict.get("id")
        is_notification = "id" not in request_dict
        method = request_dict.get("method")
        params = request_dict.get("params") or {}

        if not method or not isinstance(method, str):
            if is_notification:
                logger.warning("Received invalid MCP notification without method")
                return None
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
                requested_version = params.get("protocolVersion")
                if requested_version in SUPPORTED_PROTOCOL_VERSIONS:
                    protocol_version = requested_version
                else:
                    logger.info(
                        "Client requested unsupported or missing MCP protocolVersion '%s'; returning supported '%s'",
                        requested_version,
                        MCP_PROTOCOL_VERSION,
                    )
                    protocol_version = MCP_PROTOCOL_VERSION

                if is_notification:
                    return None

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": protocol_version,
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
                if is_notification:
                    return None
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}

            # 3. MCP ping
            if method == "ping":
                if is_notification:
                    return None
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}

            # 4. MCP tools/list
            if method == "tools/list":
                tools = self.mcp_service.list_tools()
                formatted_tools = [self._convert_tool_to_json_schema(t) for t in tools]
                if is_notification:
                    return None
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
                    if is_notification:
                        logger.warning(
                            "Invalid notification params: 'name' is required for tools/call"
                        )
                        return None
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

                if is_notification:
                    return None

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

            # 6. Generic notifications handler
            if method.startswith("notifications/"):
                logger.info("Received MCP notification '%s'", method)
                if is_notification:
                    return None
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}

            # Method not recognized
            logger.warning("Unrecognized MCP method requested: %s", method)
            if is_notification:
                return None
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
            if is_notification:
                return None
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal JSON-RPC error: {e}"},
            }
