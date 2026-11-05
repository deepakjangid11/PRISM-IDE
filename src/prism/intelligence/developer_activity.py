from __future__ import annotations

from typing import TYPE_CHECKING

from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.logging.logger import get_logger

if TYPE_CHECKING:
    from prism.intelligence.developer_session import DeveloperSessionService
    from prism.storage.repositories.base import ActivityRepository

logger = get_logger(__name__)


class ActivityRecorder:
    """Record and retain developer activity events."""

    def __init__(
        self,
        repository: ActivityRepository | None = None,
        session_service: DeveloperSessionService | None = None,
    ) -> None:
        self._activities: list[DeveloperActivity] = []
        self._repository: ActivityRepository | None = repository
        self._session_service: DeveloperSessionService | None = session_service

    def record(self, activity: DeveloperActivity) -> DeveloperActivity:
        # Automatically tag with active working session if not already provided
        effective_activity = activity
        if effective_activity.session_id is None and self._session_service is not None:
            active_session = self._session_service.get_active_session(
                effective_activity.developer_id
            )
            if active_session is not None:
                effective_activity = effective_activity.model_copy(
                    update={"session_id": active_session.session_id}
                )

        self._activities.append(effective_activity)
        if self._repository is not None:
            self._repository.save(effective_activity)

        logger.info(
            "Developer activity recorded | event_id=%s | developer_id=%s "
            "| session_id=%s | event_type=%s | project=%s | file=%s",
            effective_activity.event_id,
            effective_activity.developer_id,
            effective_activity.session_id,
            effective_activity.event_type,
            effective_activity.project_path,
            effective_activity.file_path,
        )

        return effective_activity

    def get_activities(self) -> list[DeveloperActivity]:
        """Return all recorded activities."""
        return list(self._activities)

    def get_activities_for_developer(
        self, developer_id: str, project_path: str | None = None
    ) -> list[DeveloperActivity]:
        """Fetch recorded activities for a developer, optionally filtered by project."""
        if self._repository is not None:
            return self._repository.get_by_developer(developer_id, project_path)
        return [
            a
            for a in self._activities
            if a.developer_id == developer_id
            and (project_path is None or a.project_path == project_path)
        ]

    def get_activities_for_session(self, session_id: str) -> list[DeveloperActivity]:
        """Fetch recorded activities associated with a specific working session."""
        if self._repository is not None:
            return self._repository.get_by_session(session_id)
        return [a for a in self._activities if a.session_id == session_id]

    def clear(self) -> None:
        """Clear all recorded activities."""
        self._activities.clear()
        if self._repository is not None:
            self._repository.clear()
