from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from prism.storage.models.base import Base

MYSQL_TABLE_ARGS = {
    "mysql_default_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


class DeveloperInsightRecord(Base):
    """SQLAlchemy model for structured developer insights."""

    __tablename__ = "developer_insights"

    insight_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    supporting_skills_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    actionable_recommendation: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_dev_insight_dev_time", "developer_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )


class DeveloperPerformanceSnapshotRecord(Base):
    """SQLAlchemy model for periodic developer performance checkpoints."""

    __tablename__ = "developer_performance_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )
    total_activities: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verified_skills_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    average_proficiency_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    active_knowledge_gaps_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    tasks_completed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    task_success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    learning_consistency_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    role_readiness_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    __table_args__ = (
        Index("ix_dev_snapshot_dev_time", "developer_id", "timestamp"),
        MYSQL_TABLE_ARGS,
    )


class PersonalizedTaskRecord(Base):
    """SQLAlchemy model for actionable recommended developer tasks."""

    __tablename__ = "personalized_tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_skill: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="generated", index=True
    )
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    target_role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prerequisite_skills_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    reason: Mapped[str] = mapped_column(String(1024), nullable=False)
    acceptance_criteria_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    problem_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_objectives_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=True, default=list
    )
    requirements_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=True, default=list
    )
    test_cases_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=True, default=list
    )
    hints_json: Mapped[list[Any]] = mapped_column(JSON, nullable=True, default=list)
    expected_deliverables_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=True, default=list
    )
    evaluation_criteria_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=True, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    __table_args__ = (
        Index("ix_dev_task_dev_status", "developer_id", "status"),
        MYSQL_TABLE_ARGS,
    )


class TaskOutcomeRecord(Base):
    """SQLAlchemy model for recorded outcomes of executed tasks."""

    __tablename__ = "task_outcomes"

    outcome_id: Mapped[str] = mapped_column(String(64), primary_key=True)
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
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    execution_notes: Mapped[str] = mapped_column(String(2048), nullable=False)
    verified_artifacts_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_task_outcomes_dev_time", "developer_id", "recorded_at"),
        MYSQL_TABLE_ARGS,
    )


class DeveloperFeedbackRecord(Base):
    """SQLAlchemy model for actionable developer feedback entries."""

    __tablename__ = "developer_feedbacks"

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    related_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_skill: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(2048), nullable=False)
    supporting_evidence_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    recommended_next_action: Mapped[str] = mapped_column(String(1024), nullable=False)
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    timestamp: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_dev_feedback_dev_time", "developer_id", "timestamp"),
        MYSQL_TABLE_ARGS,
    )


class MentoringSessionRecordEntity(Base):
    """SQLAlchemy model for recorded adaptive mentoring sessions."""

    __tablename__ = "mentoring_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    query: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_skill: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[str] = mapped_column(String(2048), nullable=False)
    outcome_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_mentoring_dev_time", "developer_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )


class LearningAdaptationRecord(Base):
    """SQLAlchemy model for pedagogical learning strategy adaptations."""

    __tablename__ = "learning_adaptations"

    adaptation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    new_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    adaptation_reason: Mapped[str] = mapped_column(String(1024), nullable=False)
    adjusted_difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    adjusted_priorities_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    stalled_skills_json: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    timestamp: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_dev_adapt_dev_time", "developer_id", "timestamp"),
        MYSQL_TABLE_ARGS,
    )
