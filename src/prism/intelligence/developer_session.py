import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from prism.config.settings import Settings
from prism.config.settings import settings as global_settings
from prism.intelligence.models.developer_identity_models import (
    DeveloperSession,
    SessionHistoryResponse,
    SessionStatus,
)
from prism.logging.logger import get_logger
from prism.storage.repositories.base import (
    DeveloperRepository,
    DeveloperSessionRepository,
)

logger = get_logger(__name__)


def _to_utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC timezone-aware for safe arithmetic."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class DeveloperSessionService:
    """Service governing developer working session lifecycle, heartbeats, and history."""

    def __init__(
        self,
        session_repo: DeveloperSessionRepository,
        developer_repo: DeveloperRepository,
        app_settings: Settings | None = None,
    ) -> None:
        self.session_repo = session_repo
        self.developer_repo = developer_repo
        self.settings = app_settings or global_settings

    @property
    def session_timeout_minutes(self) -> int:
        return self.settings.session_timeout_minutes

    def start_session(
        self,
        developer_id: str,
        project_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DeveloperSession:
        """Start a new working session for a developer, closing any prior active session."""
        start_time = time.perf_counter()
        cleaned_dev_id = developer_id.strip()

        # Verify developer exists
        dev = self.developer_repo.get_developer(cleaned_dev_id)
        if dev is None:
            raise ValueError(f"Developer not found: '{cleaned_dev_id}'")

        now = datetime.now(UTC)

        # Enforce single active session rule: conclude any currently active session
        existing_active = self.session_repo.get_active_session(cleaned_dev_id)
        if existing_active is not None:
            # Check staleness of existing active session
            if (
                now - _to_utc(existing_active.last_activity_at)
            ).total_seconds() > self.session_timeout_minutes * 60:
                self.session_repo.terminate_session(
                    existing_active.session_id,
                    SessionStatus.STALE.value,
                    existing_active.last_activity_at,
                )
                logger.info(
                    "Stale active session marked expired before new session | session_id=%s | dev_id=%s",
                    existing_active.session_id,
                    cleaned_dev_id,
                )
            else:
                self.session_repo.terminate_session(
                    existing_active.session_id,
                    SessionStatus.COMPLETED.value,
                    now,
                )
                logger.info(
                    "Concluded existing active session before starting new one | session_id=%s | dev_id=%s",
                    existing_active.session_id,
                    cleaned_dev_id,
                )

        session_id = f"ses_{uuid.uuid4().hex[:16]}"
        new_session = DeveloperSession(
            session_id=session_id,
            developer_id=cleaned_dev_id,
            status=SessionStatus.ACTIVE.value,
            started_at=now,
            last_activity_at=now,
            ended_at=None,
            project_path=project_path.strip() if project_path else None,
            metadata=dict(metadata or {}),
            created_at=now,
            updated_at=now,
        )

        self.session_repo.create_session(new_session)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Working session started | session_id=%s | dev_id=%s | project=%s | duration_ms=%.2f",
            session_id,
            cleaned_dev_id,
            project_path,
            duration_ms,
        )
        return new_session

    def send_heartbeat(
        self,
        session_id: str,
        developer_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> DeveloperSession:
        """Process heartbeat to extend session activity timestamp and validate state."""
        start_time = time.perf_counter()
        cleaned_session_id = session_id.strip()
        cleaned_dev_id = developer_id.strip()

        session = self.session_repo.get_session(cleaned_session_id)
        if session is None:
            raise ValueError(f"Session not found: '{cleaned_session_id}'")

        if session.developer_id != cleaned_dev_id:
            raise ValueError(
                f"Session '{cleaned_session_id}' does not belong to developer '{cleaned_dev_id}'"
            )

        if session.status != SessionStatus.ACTIVE.value:
            raise ValueError(
                f"Cannot heartbeat session '{cleaned_session_id}' in '{session.status}' state"
            )

        now = datetime.now(UTC)
        if (
            now - _to_utc(session.last_activity_at)
        ).total_seconds() > self.session_timeout_minutes * 60:
            self.session_repo.terminate_session(
                cleaned_session_id,
                SessionStatus.STALE.value,
                session.last_activity_at,
            )
            raise ValueError(
                f"Session '{cleaned_session_id}' has expired due to inactivity"
            )

        self.session_repo.touch_heartbeat(cleaned_session_id, now, metadata=metadata)

        # Retrieve fresh state
        updated = self.session_repo.get_session(cleaned_session_id)
        if updated is None:
            raise RuntimeError(
                f"Failed to reload session '{cleaned_session_id}' after heartbeat"
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(
            "Session heartbeat processed | session_id=%s | dev_id=%s | duration_ms=%.2f",
            cleaned_session_id,
            cleaned_dev_id,
            duration_ms,
        )
        return updated

    def end_session(
        self,
        session_id: str,
        developer_id: str,
        status: str = SessionStatus.COMPLETED.value,
    ) -> DeveloperSession:
        """Conclude an active working session with status update."""
        start_time = time.perf_counter()
        cleaned_session_id = session_id.strip()
        cleaned_dev_id = developer_id.strip()

        session = self.session_repo.get_session(cleaned_session_id)
        if session is None:
            raise ValueError(f"Session not found: '{cleaned_session_id}'")

        if session.developer_id != cleaned_dev_id:
            raise ValueError(
                f"Session '{cleaned_session_id}' does not belong to developer '{cleaned_dev_id}'"
            )

        # Prevent invalid repeated state transitions if already ended
        if session.status in (
            SessionStatus.COMPLETED.value,
            SessionStatus.TERMINATED.value,
            SessionStatus.STALE.value,
        ):
            logger.warning(
                "Session '%s' is already in '%s' terminal state",
                cleaned_session_id,
                session.status,
            )
            return session

        valid_terminal_statuses = {
            SessionStatus.COMPLETED.value,
            SessionStatus.TERMINATED.value,
            SessionStatus.STALE.value,
        }
        target_status = status.strip().lower()
        if target_status not in valid_terminal_statuses:
            raise ValueError(
                f"Invalid session terminal status '{status}'. Expected one of {valid_terminal_statuses}"
            )

        now = datetime.now(UTC)
        self.session_repo.terminate_session(cleaned_session_id, target_status, now)

        updated = self.session_repo.get_session(cleaned_session_id)
        if updated is None:
            raise RuntimeError(
                f"Failed to reload session '{cleaned_session_id}' after termination"
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Session concluded | session_id=%s | dev_id=%s | status=%s | duration_ms=%.2f",
            cleaned_session_id,
            cleaned_dev_id,
            target_status,
            duration_ms,
        )
        return updated

    def get_active_session(self, developer_id: str) -> DeveloperSession | None:
        """Retrieve current active working session, automatically checking for staleness."""
        cleaned_dev_id = developer_id.strip()
        session = self.session_repo.get_active_session(cleaned_dev_id)
        if session is None:
            return None

        now = datetime.now(UTC)
        if (
            now - _to_utc(session.last_activity_at)
        ).total_seconds() > self.session_timeout_minutes * 60:
            self.session_repo.terminate_session(
                session.session_id,
                SessionStatus.STALE.value,
                session.last_activity_at,
            )
            logger.info(
                "Active session detected as stale during lookup | session_id=%s | dev_id=%s",
                session.session_id,
                cleaned_dev_id,
            )
            return None

        return session

    def get_session_history(
        self,
        developer_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> SessionHistoryResponse:
        """Fetch paginated historical sessions for a developer."""
        start_time = time.perf_counter()
        cleaned_dev_id = developer_id.strip()

        if limit < 1:
            raise ValueError("Limit must be a positive integer")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        sessions, total_count = self.session_repo.list_sessions_for_developer(
            cleaned_dev_id, limit=limit, offset=offset
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Session history retrieved | dev_id=%s | count=%d | total=%d | duration_ms=%.2f",
            cleaned_dev_id,
            len(sessions),
            total_count,
            duration_ms,
        )

        return SessionHistoryResponse(
            developer_id=cleaned_dev_id,
            total_count=total_count,
            limit=limit,
            offset=offset,
            sessions=sessions,
        )

    def cleanup_stale_sessions(self, timeout_minutes: int | None = None) -> int:
        """Detect and transition expired active sessions to stale state."""
        effective_timeout = timeout_minutes or self.session_timeout_minutes
        cutoff = datetime.now(UTC) - timedelta(minutes=effective_timeout)
        stale_sessions = self.session_repo.get_stale_sessions(cutoff)

        for session in stale_sessions:
            self.session_repo.terminate_session(
                session.session_id,
                SessionStatus.STALE.value,
                session.last_activity_at,
            )

        if stale_sessions:
            logger.info(
                "Stale sessions cleaned up | count=%d | timeout_min=%d",
                len(stale_sessions),
                effective_timeout,
            )
        return len(stale_sessions)
