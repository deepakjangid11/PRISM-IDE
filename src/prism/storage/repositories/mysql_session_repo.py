from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from prism.intelligence.models.developer_identity_models import DeveloperSession
from prism.storage.database import session_scope
from prism.storage.models.session_records import DeveloperSessionRecord
from prism.storage.repositories.mysql_developer_repo import MySQLDeveloperRepository


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _record_to_session(record: DeveloperSessionRecord) -> DeveloperSession:
    """Convert an ORM DeveloperSessionRecord to domain DeveloperSession model."""
    return DeveloperSession(
        session_id=record.session_id,
        developer_id=record.developer_id,
        status=record.status,
        started_at=_ensure_utc(record.started_at),
        last_activity_at=_ensure_utc(record.last_activity_at),
        ended_at=_ensure_utc(record.ended_at) if record.ended_at else None,
        project_path=record.project_path,
        metadata=dict(record.metadata_json or {}),
        created_at=_ensure_utc(record.created_at),
        updated_at=_ensure_utc(record.updated_at),
    )


class MySQLSessionRepository:
    """MySQL-backed repository for developer working sessions."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        developer_repo: MySQLDeveloperRepository | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.developer_repo = developer_repo or MySQLDeveloperRepository(
            session_factory
        )

    def create_session(self, session: DeveloperSession) -> None:
        """Persist a new developer session after ensuring developer existence."""
        self.developer_repo.ensure_developer(session.developer_id)
        now = datetime.now(UTC)
        with session_scope(self.session_factory) as db_session:
            record = DeveloperSessionRecord(
                session_id=session.session_id,
                developer_id=session.developer_id,
                project_path=session.project_path,
                status=session.status,
                started_at=session.started_at,
                last_activity_at=session.last_activity_at,
                ended_at=session.ended_at,
                metadata_json=dict(session.metadata),
                created_at=session.created_at or now,
                updated_at=session.updated_at or now,
            )
            db_session.add(record)

    def get_session(self, session_id: str) -> DeveloperSession | None:
        """Retrieve a session by its unique session ID."""
        with session_scope(self.session_factory) as db_session:
            stmt = select(DeveloperSessionRecord).where(
                DeveloperSessionRecord.session_id == session_id
            )
            record = db_session.scalar(stmt)
            return _record_to_session(record) if record else None

    def get_active_session(self, developer_id: str) -> DeveloperSession | None:
        """Retrieve the latest active session for a developer."""
        with session_scope(self.session_factory) as db_session:
            stmt = (
                select(DeveloperSessionRecord)
                .where(
                    DeveloperSessionRecord.developer_id == developer_id,
                    DeveloperSessionRecord.status == "active",
                )
                .order_by(DeveloperSessionRecord.started_at.desc())
                .limit(1)
            )
            record = db_session.scalar(stmt)
            return _record_to_session(record) if record else None

    def update_session(self, session: DeveloperSession) -> None:
        """Update an existing session state."""
        now = datetime.now(UTC)
        with session_scope(self.session_factory) as db_session:
            stmt = select(DeveloperSessionRecord).where(
                DeveloperSessionRecord.session_id == session.session_id
            )
            record = db_session.scalar(stmt)
            if record is not None:
                record.status = session.status
                record.last_activity_at = session.last_activity_at
                record.ended_at = session.ended_at
                record.metadata_json = dict(session.metadata)
                record.updated_at = now

    def touch_heartbeat(
        self,
        session_id: str,
        last_activity_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Lightweight atomic update for last_activity_at timestamp."""
        now = datetime.now(UTC)
        with session_scope(self.session_factory) as db_session:
            if metadata:
                stmt_find = select(DeveloperSessionRecord).where(
                    DeveloperSessionRecord.session_id == session_id,
                    DeveloperSessionRecord.status == "active",
                )
                record = db_session.scalar(stmt_find)
                if not record:
                    return False
                record.last_activity_at = last_activity_at
                current_meta = dict(record.metadata_json or {})
                current_meta.update(metadata)
                record.metadata_json = current_meta
                record.updated_at = now
                return True

            stmt_update = (
                update(DeveloperSessionRecord)
                .where(
                    DeveloperSessionRecord.session_id == session_id,
                    DeveloperSessionRecord.status == "active",
                )
                .values(
                    last_activity_at=last_activity_at,
                    updated_at=now,
                )
            )
            result = db_session.execute(stmt_update)
            return cast(CursorResult[Any], result).rowcount > 0

    def list_sessions_for_developer(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[DeveloperSession], int]:
        """Retrieve paginated sessions for a developer and the total count."""
        with session_scope(self.session_factory) as db_session:
            count_stmt = select(func.count(DeveloperSessionRecord.id)).where(
                DeveloperSessionRecord.developer_id == developer_id
            )
            total = db_session.scalar(count_stmt) or 0

            stmt = (
                select(DeveloperSessionRecord)
                .where(DeveloperSessionRecord.developer_id == developer_id)
                .order_by(DeveloperSessionRecord.started_at.desc())
                .limit(limit)
                .offset(offset)
            )
            records = db_session.scalars(stmt).all()
            return [_record_to_session(r) for r in records], total

    def get_stale_sessions(self, cutoff_time: datetime) -> list[DeveloperSession]:
        """Retrieve active sessions whose last activity is before the cutoff time."""
        with session_scope(self.session_factory) as db_session:
            stmt = select(DeveloperSessionRecord).where(
                DeveloperSessionRecord.status == "active",
                DeveloperSessionRecord.last_activity_at < cutoff_time,
            )
            records = db_session.scalars(stmt).all()
            return [_record_to_session(r) for r in records]

    def terminate_session(
        self, session_id: str, status: str, ended_at: datetime
    ) -> bool:
        """Conclude an active session with the specified status and ended timestamp."""
        now = datetime.now(UTC)
        with session_scope(self.session_factory) as db_session:
            stmt = (
                update(DeveloperSessionRecord)
                .where(DeveloperSessionRecord.session_id == session_id)
                .values(
                    status=status,
                    ended_at=ended_at,
                    updated_at=now,
                )
            )
            result = db_session.execute(stmt)
            return cast(CursorResult[Any], result).rowcount > 0

    def clear(self, developer_id: str | None = None) -> None:
        """Remove sessions, optionally filtered by developer."""
        with session_scope(self.session_factory) as db_session:
            stmt = delete(DeveloperSessionRecord)
            if developer_id is not None:
                stmt = stmt.where(DeveloperSessionRecord.developer_id == developer_id)
            db_session.execute(stmt)
