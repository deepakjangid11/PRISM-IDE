from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from prism.storage.models.base import Base


class SkillRecord(Base):
    """SQLAlchemy model for the skills master catalog."""

    __tablename__ = "skills"

    skill_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=lambda: datetime.now(UTC)
    )


class SkillRelationshipRecord(Base):
    """SQLAlchemy model for directed relationships between technical skills."""

    __tablename__ = "skill_relationships"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    from_skill_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_skill_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "from_skill_id",
            "to_skill_id",
            "relationship_type",
            name="uq_skill_rel_edge",
        ),
    )


class SkillEvidenceRecord(Base):
    """SQLAlchemy model for concrete skill evidence items."""

    __tablename__ = "skill_evidence"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, index=True
    )
    project_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    __table_args__ = (Index("ix_skill_ev_lookup", "developer_id", "skill_id"),)


class DeveloperSkillRecord(Base):
    """SQLAlchemy model for materialized developer skill competence."""

    __tablename__ = "developer_skills"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    developer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("developers.developer_id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        nullable=False,
    )
    proficiency_level: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_sufficient_evidence: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    last_assessed: Mapped[datetime | None] = mapped_column(
        DATETIME(fsp=6), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("developer_id", "skill_id", name="uq_dev_skill_pair"),
        Index("ix_dev_skills_lookup", "developer_id", "skill_id"),
    )
