from __future__ import annotations

from typing import TYPE_CHECKING

from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.logging.logger import get_logger

if TYPE_CHECKING:
    from prism.storage.repositories.base import ActivityRepository

logger = get_logger(__name__)


class ActivityRecorder:
    """Record and retain developer activity events."""

    def __init__(self, repository: ActivityRepository | None = None) -> None:
        self._activities: list[DeveloperActivity] = []
        self._repository: ActivityRepository | None = repository

    def record(self, activity: DeveloperActivity) -> DeveloperActivity:
        self._activities.append(activity)
        if self._repository is not None:
            self._repository.save(activity)

        logger.info(
            "Developer activity recorded | event_id=%s | developer_id=%s "
            "| event_type=%s | project=%s | file=%s",
            activity.event_id,
            activity.developer_id,
            activity.event_type,
            activity.project_path,
            activity.file_path,
        )

        return activity

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

    def clear(self) -> None:
        """Clear all recorded activities."""
        self._activities.clear()
        if self._repository is not None:
            self._repository.clear()
