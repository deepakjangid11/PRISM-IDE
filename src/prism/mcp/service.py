import inspect
import os
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from prism.evaluation.engine import TaskEvaluationEngine
from prism.intelligence.models.task_platform_models import MCPAuditLog
from prism.intelligence.task_recommendation_engine import (
    TaskRecommendationEngine,
)
from prism.logging.logger import get_logger
from prism.rag.schemas import RAGQueryRequest
from prism.rag.service import RAGService
from prism.reporting.report_generator import DeveloperReportGenerator
from prism.storage.repositories.base import TaskPlatformRepository

logger = get_logger(__name__)


class MCPToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    parameters: list[MCPToolParameter]


class ToolExecutionResult(BaseModel):
    tool_name: str
    status: str  # "success" or "error"
    data: Any | None = None
    error: str | None = None
    duration_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


BLOCKED_FILE_PATTERNS = {
    ".env",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "alembic.ini",
    "password",
    "secret",
}


class MCPService:
    """Production Model Context Protocol service providing controlled, safe AI tools and resources."""

    def __init__(
        self,
        task_platform_repo: TaskPlatformRepository,
        task_engine: TaskRecommendationEngine,
        evaluation_engine: TaskEvaluationEngine,
        report_generator: DeveloperReportGenerator,
        rag_service: RAGService | None = None,
        workspace_root: str | None = None,
    ) -> None:
        self.task_platform_repo = task_platform_repo
        self.task_engine = task_engine
        self.evaluation_engine = evaluation_engine
        self.report_generator = report_generator
        self.rag_service = rag_service
        self.workspace_root = (
            Path(workspace_root).resolve()
            if workspace_root
            else Path(os.getcwd()).resolve()
        )

        self._tools: dict[str, tuple[MCPToolDefinition, Callable[..., Any]]] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register vetted, authorized tools."""
        self.register_tool(
            definition=MCPToolDefinition(
                name="get_developer_task",
                description="Retrieve complete task details, requirements, acceptance criteria, and progressive hints.",
                parameters=[
                    MCPToolParameter(
                        name="task_id",
                        type="string",
                        description="Unique task identifier",
                        required=True,
                    )
                ],
            ),
            handler=self._tool_get_developer_task,
        )

        self.register_tool(
            definition=MCPToolDefinition(
                name="read_project_file",
                description="Read an authorized project source file within workspace boundaries.",
                parameters=[
                    MCPToolParameter(
                        name="file_path",
                        type="string",
                        description="Relative path of file to read",
                        required=True,
                    )
                ],
            ),
            handler=self._tool_read_project_file,
        )

        self.register_tool(
            definition=MCPToolDefinition(
                name="get_task_progress",
                description="Retrieve task progression, counts, and completion statuses for a developer.",
                parameters=[
                    MCPToolParameter(
                        name="developer_id",
                        type="string",
                        description="Unique developer identifier",
                        required=True,
                    )
                ],
            ),
            handler=self._tool_get_task_progress,
        )

        self.register_tool(
            definition=MCPToolDefinition(
                name="search_knowledge_docs",
                description="Search authorized programming, architectural, and learning documentation via RAG.",
                parameters=[
                    MCPToolParameter(
                        name="query",
                        type="string",
                        description="Semantic search query",
                        required=True,
                    ),
                    MCPToolParameter(
                        name="top_k",
                        type="integer",
                        description="Max number of results (1-10)",
                        required=False,
                    ),
                ],
            ),
            handler=self._tool_search_knowledge_docs,
        )

        self.register_tool(
            definition=MCPToolDefinition(
                name="submit_task_evaluation",
                description="Trigger automated static analysis and acceptance criteria evaluation for a task submission.",
                parameters=[
                    MCPToolParameter(
                        name="submission_id",
                        type="string",
                        description="Unique submission identifier",
                        required=True,
                    )
                ],
            ),
            handler=self._tool_submit_task_evaluation,
        )

        self.register_tool(
            definition=MCPToolDefinition(
                name="get_developer_report",
                description="Retrieve or generate a comprehensive periodic performance and learning report.",
                parameters=[
                    MCPToolParameter(
                        name="developer_id",
                        type="string",
                        description="Developer identifier",
                        required=True,
                    ),
                    MCPToolParameter(
                        name="period_type",
                        type="string",
                        description="Period: 'daily', 'weekly', 'monthly'",
                        required=False,
                    ),
                ],
            ),
            handler=self._tool_get_developer_report,
        )

    def register_tool(
        self, definition: MCPToolDefinition, handler: Callable[..., Any]
    ) -> None:
        """Register a new MCP tool definition with its execution handler."""
        self._tools[definition.name] = (definition, handler)

    def list_tools(self) -> list[MCPToolDefinition]:
        """List all available MCP tools."""
        return [tool_def for tool_def, _ in self._tools.values()]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        caller_id: str | None = None,
    ) -> ToolExecutionResult:
        """Execute an authorized tool with timing, input validation, permission guards, and audit logging."""
        cleaned_tool = tool_name.strip()
        start = time.perf_counter()

        if cleaned_tool not in self._tools:
            duration = (time.perf_counter() - start) * 1000.0
            self._log_audit(
                cleaned_tool,
                caller_id,
                arguments,
                "error",
                duration,
            )
            return ToolExecutionResult(
                tool_name=cleaned_tool,
                status="error",
                error=f"Tool '{cleaned_tool}' is not registered or supported.",
                duration_ms=round(duration, 2),
            )

        tool_def, handler = self._tools[cleaned_tool]

        # Validate required parameters
        for param in tool_def.parameters:
            if param.required and param.name not in arguments:
                duration = (time.perf_counter() - start) * 1000.0
                self._log_audit(
                    cleaned_tool,
                    caller_id,
                    arguments,
                    "validation_failed",
                    duration,
                )
                return ToolExecutionResult(
                    tool_name=cleaned_tool,
                    status="error",
                    error=f"Missing required argument '{param.name}'",
                    duration_ms=round(duration, 2),
                )

        # Enforce developer authorization / IDOR guards for developer-specific tools
        if cleaned_tool in ("get_task_progress", "get_developer_report"):
            target_dev_id = arguments.get("developer_id")
            if (
                target_dev_id
                and caller_id
                and caller_id != "admin"
                and str(target_dev_id).strip() != str(caller_id).strip()
            ):
                duration = (time.perf_counter() - start) * 1000.0
                self._log_audit(
                    cleaned_tool,
                    caller_id,
                    arguments,
                    "unauthorized",
                    duration,
                )
                return ToolExecutionResult(
                    tool_name=cleaned_tool,
                    status="error",
                    error=f"Unauthorized: Caller '{caller_id}' cannot access developer '{target_dev_id}' records.",
                    duration_ms=round(duration, 2),
                )

        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            duration = (time.perf_counter() - start) * 1000.0
            self._log_audit(
                cleaned_tool,
                caller_id,
                arguments,
                "success",
                duration,
            )
            return ToolExecutionResult(
                tool_name=cleaned_tool,
                status="success",
                data=result,
                duration_ms=round(duration, 2),
            )
        except Exception as err:
            logger.exception("Error executing MCP tool '%s'", cleaned_tool)
            duration = (time.perf_counter() - start) * 1000.0
            self._log_audit(
                cleaned_tool,
                caller_id,
                arguments,
                "execution_error",
                duration,
            )
            return ToolExecutionResult(
                tool_name=cleaned_tool,
                status="error",
                error=str(err),
                duration_ms=round(duration, 2),
            )

    def _log_audit(
        self,
        tool_name: str,
        caller_id: str | None,
        args: dict[str, Any],
        status: str,
        duration_ms: float,
    ) -> None:
        """Persist audit record for tool usage."""
        summary = f"args={list(args.keys())}"
        audit = MCPAuditLog(
            log_id=f"mcp_{uuid.uuid4().hex[:12]}",
            tool_name=tool_name,
            caller_id=caller_id,
            input_summary=summary,
            status=status,
            duration_ms=round(duration_ms, 2),
            timestamp=datetime.now(UTC),
        )
        try:
            self.task_platform_repo.save_mcp_audit(audit)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to persist MCP audit log for '%s'", tool_name)

    # =========================================================================
    # TOOL HANDLERS
    # =========================================================================

    def _tool_get_developer_task(self, task_id: str) -> dict[str, Any]:
        task = self.task_engine.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID '{task_id}' was not found.")
        return task.model_dump()

    def _tool_read_project_file(self, file_path: str) -> dict[str, Any]:
        """Safely read authorized source files, rejecting path traversal, absolute drives, and sensitive files."""
        clean_path = file_path.strip().replace("\\", "/")
        if ":" in clean_path:
            raise PermissionError("Access denied: Absolute volume paths are forbidden.")
        clean_path = clean_path.lstrip("/")
        for blocked in BLOCKED_FILE_PATTERNS:
            if blocked in clean_path.lower():
                raise PermissionError(
                    f"Access to '{clean_path}' is restricted for security."
                )

        target_path = (self.workspace_root / clean_path).resolve()
        try:
            target_path.relative_to(self.workspace_root)
        except ValueError as err:
            raise PermissionError(
                "Access denied: Path traversal outside workspace boundary is forbidden."
            ) from err

        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"File '{clean_path}' not found.")

        # Limit file read size to 1MB
        if target_path.stat().st_size > 1_048_576:
            raise ValueError("File exceeds maximum allowed size (1 MB).")

        content = target_path.read_text(encoding="utf-8", errors="replace")
        return {
            "file_path": clean_path,
            "size_bytes": len(content.encode("utf-8")),
            "content": content,
        }

    def _tool_get_task_progress(self, developer_id: str) -> dict[str, Any]:
        tasks = self.task_platform_repo.get_submissions_for_developer(
            developer_id, limit=100
        )
        evals = self.task_platform_repo.get_evaluations_for_developer(
            developer_id, limit=100
        )
        passed = sum(1 for e in evals if e.passed)
        avg_score = sum(e.score for e in evals) / len(evals) if evals else 0.0
        return {
            "developer_id": developer_id,
            "total_submissions": len(tasks),
            "total_evaluations": len(evals),
            "passed_evaluations": passed,
            "average_score": round(avg_score, 1),
        }

    async def _tool_search_knowledge_docs(
        self, query: str, top_k: int = 3
    ) -> list[dict[str, Any]]:
        if not self.rag_service:
            return [{"warning": "RAG knowledge service is not configured."}]
        clamped_k = min(max(top_k, 1), 10)
        req = RAGQueryRequest(query=query, top_k=clamped_k)
        results = await self.rag_service.search(req)
        return [r.model_dump() for r in results.chunks]

    def _tool_submit_task_evaluation(self, submission_id: str) -> dict[str, Any]:
        evaluation = self.evaluation_engine.evaluate_submission(submission_id)
        return evaluation.model_dump()

    def _tool_get_developer_report(
        self, developer_id: str, period_type: str = "weekly"
    ) -> dict[str, Any]:
        report = self.report_generator.generate_report(
            developer_id=developer_id, period_type=period_type
        )
        return report.model_dump()
