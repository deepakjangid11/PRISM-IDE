from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class ActivityRecorder:
    """Record and retain developer activity events."""

    def __init__(self) -> None:
        self._activities: list[DeveloperActivity] = []

    def record(self, activity: DeveloperActivity) -> DeveloperActivity:
        self._activities.append(activity)

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

    def clear(self) -> None:
        """Clear all recorded activities."""
        self._activities.clear()
