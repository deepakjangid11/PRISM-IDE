from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from prism.api.dependencies import mcp_service, task_platform_repo
from prism.intelligence.models.task_platform_models import MCPAuditLog
from prism.mcp.service import MCPToolDefinition, ToolExecutionResult

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])


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
) -> ToolExecutionResult:
    """Execute an authorized MCP tool with permission checks, timing, and audit logging."""
    result = await mcp_service.execute_tool(
        tool_name=request.tool_name,
        arguments=request.arguments,
        caller_id=request.caller_id,
    )
    if result.status == "error" and "not registered" in (result.error or ""):
        raise HTTPException(status_code=404, detail=result.error)
    return result


@router.get("/audit", response_model=list[MCPAuditLog])
async def get_mcp_audit_logs(
    caller_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[MCPAuditLog]:
    """Retrieve audit logs of executed MCP tools."""
    return task_platform_repo.get_mcp_audits(caller_id=caller_id, limit=limit)
