import sys
from datetime import UTC, datetime, timedelta

from prism.exceptions.custom_exception import CustomException
from prism.intelligence.models.activity_session_models import (
    ActivitySession,
    ActivitySessionMetrics,
)
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)

DEFAULT_INACTIVITY_THRESHOLD = timedelta(minutes=30)


def _normalize_timestamp(dt: datetime) -> datetime:
    """Ensure timestamp has a timezone (defaults to UTC if naive) for safe comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class ActivitySessionAnalyzer:
    """Analyze developer activity streams into time-windowed discrete sessions."""

    def __init__(
        self,
        default_inactivity_threshold: timedelta = DEFAULT_INACTIVITY_THRESHOLD,
    ) -> None:
        self.default_inactivity_threshold = default_inactivity_threshold

    def analyze(
        self,
        activities: list[DeveloperActivity],
        inactivity_threshold: timedelta | None = None,
        developer_id: str | None = None,
        project_path: str | None = None,
    ) -> ActivitySessionMetrics:
        """Analyze a list of developer activity events into sessions and aggregated metrics.

        Args:
            activities: List of DeveloperActivity events to analyze.
            inactivity_threshold: Optional override for the session inactivity threshold.
            developer_id: Optional expected developer ID (used for validation or empty list fallback).
            project_path: Optional expected project path (used for validation or empty list fallback).

        Returns:
            ActivitySessionMetrics containing session details and time-based metrics.

        Raises:
            ValueError: If activities belong to different developers or projects.
            CustomException: If an unexpected error occurs during analysis.
        """
        threshold = (
            inactivity_threshold
            if inactivity_threshold is not None
            else self.default_inactivity_threshold
        )

        logger.info(
            "Starting developer activity session analysis | events=%d | threshold=%s",
            len(activities),
            threshold,
        )

        if not activities:
            metrics = ActivitySessionMetrics(
                developer_id=developer_id or "",
                project_path=project_path or "",
                first_activity_timestamp=None,
                last_activity_timestamp=None,
                total_sessions=0,
                total_events=0,
                total_active_duration=timedelta(0),
                average_session_duration=timedelta(0),
                longest_session_duration=timedelta(0),
                average_events_per_hour=0.0,
                sessions=[],
            )
            logger.info("Completed developer activity session analysis | empty input")
            return metrics

        # Validate developer and project consistency
        first_dev_id = activities[0].developer_id
        first_proj_path = activities[0].project_path

        if any(
            a.developer_id != first_dev_id or a.project_path != first_proj_path
            for a in activities
        ):
            raise ValueError(
                "All activities must belong to the same developer and project"
            )

        if developer_id is not None and first_dev_id != developer_id:
            raise ValueError(
                "All activities must belong to the same developer and project"
            )

        if project_path is not None and first_proj_path != project_path:
            raise ValueError(
                "All activities must belong to the same developer and project"
            )

        try:
            # Sort activities chronologically
            sorted_activities = sorted(
                activities, key=lambda a: _normalize_timestamp(a.timestamp)
            )

            sessions: list[ActivitySession] = []
            current_session_events: list[DeveloperActivity] = [sorted_activities[0]]
            session_counter = 1

            for current_activity in sorted_activities[1:]:
                prev_activity = current_session_events[-1]
                time_diff = _normalize_timestamp(
                    current_activity.timestamp
                ) - _normalize_timestamp(prev_activity.timestamp)

                if time_diff <= threshold:
                    current_session_events.append(current_activity)
                else:
                    # Finalize current session
                    sessions.append(
                        self._build_session(
                            session_id=f"session_{session_counter}",
                            developer_id=first_dev_id,
                            project_path=first_proj_path,
                            events=current_session_events,
                        )
                    )
                    session_counter += 1
                    current_session_events = [current_activity]

            # Finalize trailing session
            if current_session_events:
                sessions.append(
                    self._build_session(
                        session_id=f"session_{session_counter}",
                        developer_id=first_dev_id,
                        project_path=first_proj_path,
                        events=current_session_events,
                    )
                )

            total_sessions = len(sessions)
            total_events = len(sorted_activities)
            total_active_duration = sum((s.duration for s in sessions), timedelta(0))
            average_session_duration = (
                total_active_duration / total_sessions
                if total_sessions > 0
                else timedelta(0)
            )
            longest_session_duration = (
                max((s.duration for s in sessions), default=timedelta(0))
                if sessions
                else timedelta(0)
            )

            total_active_seconds = total_active_duration.total_seconds()
            if total_active_seconds > 0:
                events_per_hour = round(
                    total_events / (total_active_seconds / 3600.0), 2
                )
            else:
                events_per_hour = 0.0

            metrics = ActivitySessionMetrics(
                developer_id=first_dev_id,
                project_path=first_proj_path,
                first_activity_timestamp=sorted_activities[0].timestamp,
                last_activity_timestamp=sorted_activities[-1].timestamp,
                total_sessions=total_sessions,
                total_events=total_events,
                total_active_duration=total_active_duration,
                average_session_duration=average_session_duration,
                longest_session_duration=longest_session_duration,
                average_events_per_hour=events_per_hour,
                sessions=sessions,
            )

            logger.info(
                "Completed developer activity session analysis | developer_id=%s | "
                "project=%s | sessions=%d | events=%d | active_duration=%s | events_per_hour=%.2f",
                first_dev_id,
                first_proj_path,
                total_sessions,
                total_events,
                total_active_duration,
                events_per_hour,
            )

            return metrics

        except ValueError:
            raise
        except Exception as error:
            logger.error(
                "Unexpected error during developer activity session analysis: %s",
                error,
            )
            raise CustomException(error, sys) from error

    @staticmethod
    def _build_session(
        session_id: str,
        developer_id: str,
        project_path: str,
        events: list[DeveloperActivity],
    ) -> ActivitySession:
        start_time = events[0].timestamp
        end_time = events[-1].timestamp
        duration = _normalize_timestamp(end_time) - _normalize_timestamp(start_time)
        duration = max(duration, timedelta(0))

        return ActivitySession(
            session_id=session_id,
            developer_id=developer_id,
            project_path=project_path,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            events=list(events),
        )
