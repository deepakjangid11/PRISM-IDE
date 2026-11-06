from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SubmissionType(StrEnum):
    """Supported types of developer submissions."""

    CODE = "code"
    FILE_TREE = "file_tree"
    GIT_REPO = "git_repo"


class SubmissionStatus(StrEnum):
    """Lifecycle status of a developer submission."""

    SUBMITTED = "submitted"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    REJECTED = "rejected"


class EvaluationCompletionStatus(StrEnum):
    """Status returned by task evaluation engine."""

    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVISION = "needs_revision"


class TaskSubmission(BaseModel):
    """Submission payload representing developer work on a task."""

    model_config = ConfigDict(extra="forbid")

    submission_id: str
    task_id: str
    developer_id: str
    submission_type: SubmissionType = SubmissionType.CODE
    source_code: str | None = None
    file_tree: dict[str, str] = Field(default_factory=dict)
    repo_url: str | None = None
    explanation: str | None = None
    status: SubmissionStatus = SubmissionStatus.SUBMITTED
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TestCaseResult(BaseModel):
    """Result of an individual test case or acceptance check."""

    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    description: str = ""
    error_message: str | None = None
    execution_time_ms: float = 0.0


class DetailedTaskEvaluation(BaseModel):
    """Comprehensive, structured evaluation result for a developer submission."""

    model_config = ConfigDict(extra="forbid")

    evaluation_id: str
    submission_id: str
    task_id: str
    developer_id: str
    passed: bool
    score: float = Field(..., ge=0.0, le=100.0)
    completion_status: EvaluationCompletionStatus
    strengths: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    test_results: list[TestCaseResult] = Field(default_factory=list)
    feedback_message: str
    generated_evidence_id: str | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GuidanceLevel(int):
    """Guidance levels 1 to 6 for interactive AI mentoring."""

    CONCEPTUAL = 1
    APPROACH = 2
    HINTS = 3
    STEP_BY_STEP = 4
    CODE_CONCEPTS = 5
    DEBUGGING = 6


class MentoringConversation(BaseModel):
    """Interactive guided learning conversation tied to a developer task."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    task_id: str | None = None
    developer_id: str
    title: str
    current_guidance_level: int = 1
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MentoringMessage(BaseModel):
    """An individual message in a task-linked mentoring conversation."""

    model_config = ConfigDict(extra="forbid")

    message_id: str
    conversation_id: str
    sender: str  # 'developer' or 'mentor'
    content: str
    guidance_level: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeveloperReport(BaseModel):
    """Comprehensive periodic performance and learning progress report."""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    developer_id: str
    period_type: str  # daily, weekly, monthly, custom
    start_date: datetime
    end_date: datetime
    metrics: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPAuditLog(BaseModel):
    """Audit log entry for Model Context Protocol tool execution."""

    model_config = ConfigDict(extra="forbid")

    log_id: str
    tool_name: str
    caller_id: str | None = None
    input_summary: str
    status: str
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
