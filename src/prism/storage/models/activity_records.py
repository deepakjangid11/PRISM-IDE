from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from prism.storage.models.base import Base


class DeveloperActivityRecord(Base):
    """SQLAlchemy model for recorded developer activity events."""

    __tablename__ = "developer_activities"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    project_path: Mapped[str] = mapped_column(String(512), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    __table_args__ = (Index("ix_dev_act_dev_time", "developer_id", "timestamp"),)
