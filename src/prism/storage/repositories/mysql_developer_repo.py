from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from prism.storage.database import session_scope
from prism.storage.models.developer_records import DeveloperRecord


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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
                "created_at": _ensure_utc(record.created_at),
                "updated_at": _ensure_utc(record.updated_at),
            }

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Fetch developer metadata by email address."""
        cleaned_email = email.strip().lower()
        if not cleaned_email:
            return None
        with session_scope(self.session_factory) as session:
            stmt = select(DeveloperRecord).where(DeveloperRecord.email == cleaned_email)
            record = session.scalar(stmt)
            if record is None:
                return None
            return {
                "developer_id": record.developer_id,
                "name": record.name,
                "email": record.email,
                "created_at": _ensure_utc(record.created_at),
                "updated_at": _ensure_utc(record.updated_at),
            }

    def create_developer(
        self,
        developer_id: str,
        name: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        """Create a new developer record, rejecting duplicates."""
        cleaned_id = developer_id.strip()
        if not cleaned_id:
            raise ValueError("Developer ID cannot be empty")
        cleaned_email = email.strip().lower() if email else None

        # Pre-validate uniqueness before opening transactional scope to prevent wrapping in CustomException
        if self.get_developer(cleaned_id) is not None:
            raise ValueError(f"Developer with ID '{cleaned_id}' already exists")

        if cleaned_email and self.get_by_email(cleaned_email) is not None:
            raise ValueError(f"Developer with email '{cleaned_email}' already exists")

        now = datetime.now(UTC)
        with session_scope(self.session_factory) as session:
            record = DeveloperRecord(
                developer_id=cleaned_id,
                name=name,
                email=cleaned_email,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.flush()
            return {
                "developer_id": record.developer_id,
                "name": record.name,
                "email": record.email,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }

    def update_developer(
        self,
        developer_id: str,
        name: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any] | None:
        """Update permitted developer profile fields."""
        cleaned_id = developer_id.strip()
        existing = self.get_developer(cleaned_id)
        if existing is None:
            return None

        if email is not None:
            cleaned_email = email.strip().lower() if email.strip() else None
            if cleaned_email and cleaned_email != existing.get("email"):
                existing_email_dev = self.get_by_email(cleaned_email)
                if (
                    existing_email_dev is not None
                    and existing_email_dev["developer_id"] != cleaned_id
                ):
                    raise ValueError(
                        f"Email '{cleaned_email}' is already registered to another developer"
                    )

        now = datetime.now(UTC)
        with session_scope(self.session_factory) as session:
            stmt = select(DeveloperRecord).where(
                DeveloperRecord.developer_id == cleaned_id
            )
            record = session.scalar(stmt)
            if record is None:
                return None

            if email is not None:
                record.email = email.strip().lower() if email.strip() else None
            if name is not None:
                record.name = name.strip() if name.strip() else None

            record.updated_at = now
            session.flush()
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
