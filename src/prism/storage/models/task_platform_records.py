from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from prism.storage.models.base import Base

MYSQL_TABLE_ARGS = {
    "mysql_default_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


class TaskSubmissionRecord(Base):
    """SQLAlchemy model for developer work submissions against assigned tasks."""

    __tablename__ = "task_submissions"

    submission_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("personalized_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="code"
    )
    source_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_tree_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    repo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    submitted_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    __table_args__ = (
        Index("ix_submissions_dev_time", "developer_id", "submitted_at"),
        MYSQL_TABLE_ARGS,
    )


class TaskEvaluationRecord(Base):
    """SQLAlchemy model for structured automated evaluations of task submissions."""

    __tablename__ = "task_evaluations"

    evaluation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    submission_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("task_submissions.submission_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("personalized_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completion_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="needs_revision"
    )
    strengths_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    mistakes_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    missing_requirements_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    improvement_suggestions_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    recommended_next_steps_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    test_results_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    feedback_message: Mapped[str] = mapped_column(Text, nullable=False)
    generated_evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    __table_args__ = (
        Index("ix_evaluations_dev_time", "developer_id", "evaluated_at"),
        MYSQL_TABLE_ARGS,
    )


class MentoringConversationRecord(Base):
    """SQLAlchemy model for persistent interactive mentoring sessions linked to tasks."""

    __tablename__ = "mentoring_conversations"

    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("personalized_tasks.task_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    current_guidance_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_mentor_conv_dev_time", "developer_id", "updated_at"),
        MYSQL_TABLE_ARGS,
    )


class MentoringMessageRecord(Base):
    """SQLAlchemy model for messages in a progressive guided mentoring dialogue."""

    __tablename__ = "mentoring_messages"

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("mentoring_conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'developer' or 'mentor'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    guidance_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    __table_args__ = (
        Index("ix_mentor_msg_conv_time", "conversation_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )


class DeveloperReportRecord(Base):
    """SQLAlchemy model for comprehensive periodic developer progress reports."""

    __tablename__ = "developer_reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # daily, weekly, monthly, custom
    start_date: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    content_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    generated_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    __table_args__ = (
        Index("ix_dev_reports_dev_time", "developer_id", "generated_at"),
        MYSQL_TABLE_ARGS,
    )


class MCPAuditLogRecord(Base):
    """SQLAlchemy model for auditing Model Context Protocol tool execution."""

    __tablename__ = "mcp_audit_logs"

    log_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    caller_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    input_summary: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    __table_args__ = (MYSQL_TABLE_ARGS,)
