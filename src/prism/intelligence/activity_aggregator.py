from collections import Counter

from prism.intelligence.models.activity_metrics_models import ActivityMetrics
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class ActivityAggregator:
    """Aggregate developer activity events into measurable metrics."""

    def aggregate(
        self,
        activities: list[DeveloperActivity],
    ) -> ActivityMetrics:
        if not activities:
            raise ValueError("At least one activity is required")

        developer_id = activities[0].developer_id
        project_path = activities[0].project_path

        if any(
            activity.developer_id != developer_id
            or activity.project_path != project_path
            for activity in activities
        ):
            raise ValueError(
                "All activities must belong to the same developer and project"
            )

        event_counts = Counter(activity.event_type for activity in activities)

        files_touched = {
            activity.file_path
            for activity in activities
            if activity.file_path is not None
        }

        metrics = ActivityMetrics(
            developer_id=developer_id,
            project_path=project_path,
            total_events=len(activities),
            code_edits=event_counts["code_edit"],
            file_opens=event_counts["file_open"],
            file_saves=event_counts["file_save"],
            test_runs=event_counts["test_run"],
            test_failures=event_counts["test_failure"],
            test_successes=event_counts["test_success"],
            errors=event_counts["error"],
            ai_help_requests=event_counts["ai_help"],
            files_touched=len(files_touched),
        )

        logger.info(
            "Developer activity aggregated | developer_id=%s | "
            "project=%s | events=%s | files=%s",
            developer_id,
            project_path,
            metrics.total_events,
            metrics.files_touched,
        )

        return metrics
