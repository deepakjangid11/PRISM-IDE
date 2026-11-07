import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from prism.api.dependencies import mcp_service, task_platform_repo
from prism.intelligence.models.task_platform_models import MCPAuditLog
from prism.mcp.protocol import MCPProtocolHandler
from prism.mcp.service import MCPToolDefinition, ToolExecutionResult
from prism.security import get_optional_current_user

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])
_protocol_handler = MCPProtocolHandler(mcp_service)


class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    caller_id: str | None = None


@router.get("/tools", response_model=list[MCPToolDefinition])
async def list_mcp_tools() -> list[MCPToolDefinition]:
    """List all registered, authorized Model Context Protocol tools and schemas."""
    return mcp_service.list_tools()


@router.post("/tools/execute", response_model=ToolExecutionResult)
async def execute_mcp_tool(
    request: ToolExecutionRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> ToolExecutionResult:
    """Execute an authorized MCP tool with permission checks, timing, and audit logging."""
    effective_caller = request.caller_id
    if current_user and not effective_caller:
        effective_caller = current_user.get("sub")

    result = await mcp_service.execute_tool(
        tool_name=request.tool_name,
        arguments=request.arguments,
        caller_id=effective_caller,
    )
    if result.status == "error" and "not registered" in (result.error or ""):
        raise HTTPException(status_code=404, detail=result.error)
    return result


@router.post("/rpc")
async def handle_mcp_jsonrpc(
    request: Request,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> Response:
    """Standard Model Context Protocol (MCP) JSON-RPC 2.0 endpoint.

    Supports official MCP methods: initialize, notifications/initialized, ping,
    tools/list, and tools/call.
    """
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON was received",
                },
            },
        )

    if not isinstance(body, dict):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: must be a JSON object",
                },
            },
        )

    caller_id = current_user.get("sub") if current_user else None
    result = await _protocol_handler.handle_request(body, caller_id=caller_id)
    if result is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@router.get("/audit", response_model=list[MCPAuditLog])
async def get_mcp_audit_logs(
    caller_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[MCPAuditLog]:
    """Retrieve audit logs of executed MCP tools."""
    return task_platform_repo.get_mcp_audits(caller_id=caller_id, limit=limit)
