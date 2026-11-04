from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from prism.storage.database import session_scope
from prism.storage.models.developer_records import DeveloperRecord


class MySQLDeveloperRepository:
    """MySQL-backed repository for developer master records."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def ensure_developer(
        self,
        developer_id: str,
        name: str | None = None,
        email: str | None = None,
    ) -> None:
        """Create developer master record if not present, or touch updated timestamp."""
        cleaned_id = developer_id.strip()
        if not cleaned_id:
            raise ValueError("Developer ID cannot be empty")

        now = datetime.now(UTC)
        with session_scope(self.session_factory) as session:
            stmt = select(DeveloperRecord).where(
                DeveloperRecord.developer_id == cleaned_id
            )
            existing = session.scalar(stmt)
            if existing is None:
                record = DeveloperRecord(
                    developer_id=cleaned_id,
                    name=name,
                    email=email,
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
            else:
                existing.updated_at = now
                if name:
                    existing.name = name
                if email:
                    existing.email = email

    def get_developer(self, developer_id: str) -> dict[str, Any] | None:
        """Fetch developer metadata by ID."""
        with session_scope(self.session_factory) as session:
            stmt = select(DeveloperRecord).where(
                DeveloperRecord.developer_id == developer_id.strip()
            )
            record = session.scalar(stmt)
            if record is None:
                return None
            return {
                "developer_id": record.developer_id,
                "name": record.name,
                "email": record.email,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }

    def list_developers(self) -> list[str]:
        """Return list of all registered developer IDs."""
        with session_scope(self.session_factory) as session:
            stmt = select(DeveloperRecord.developer_id).order_by(
                DeveloperRecord.developer_id
            )
            return list(session.scalars(stmt).all())
