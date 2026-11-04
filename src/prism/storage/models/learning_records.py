from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from prism.storage.models.base import Base


class LearningProgressRecord(Base):
    """SQLAlchemy model for active developer learning roadmaps."""

    __tablename__ = "learning_progress"

    progress_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_goal_skill_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        nullable=False,
    )
    completion_percentage: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
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
        UniqueConstraint(
            "developer_id",
            "target_goal_skill_id",
            name="uq_learning_dev_goal",
        ),
    )


class LearningProgressItemRecord(Base):
    """SQLAlchemy model for normalized steps along an active learning roadmap."""

    __tablename__ = "learning_progress_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    progress_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_progress.progress_id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DATETIME(fsp=6), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "progress_id", "skill_id", name="uq_learning_item_progress_skill"
        ),
        Index("ix_learning_item_status", "progress_id", "status"),
    )


class LearningProgressHistoryRecord(Base):
    """SQLAlchemy model for point-in-time progression checkpoints."""

    __tablename__ = "learning_progress_history"

    history_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    progress_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_progress.progress_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
    )
    target_goal_skill_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        nullable=False,
    )
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_learning_hist_dev_time", "developer_id", "recorded_at"),
    )
