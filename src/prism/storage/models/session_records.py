from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from prism.storage.models.base import Base


class DeveloperSessionRecord(Base):
    """SQLAlchemy model for persistent developer working sessions."""

    __tablename__ = "developer_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
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
        Index("ix_dev_sessions_dev_status", "developer_id", "status"),
        Index("ix_dev_sessions_dev_started", "developer_id", "started_at"),
    )
