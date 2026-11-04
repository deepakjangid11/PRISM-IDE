import sys

from prism.exceptions.custom_exception import CustomException
from prism.intelligence.activity_aggregator import ActivityAggregator
from prism.intelligence.activity_session_analyzer import (
    ActivitySessionAnalyzer,
)
from prism.intelligence.models.activity_metrics_models import ActivityMetrics
from prism.intelligence.models.activity_session_models import (
    ActivitySessionMetrics,
)
from prism.intelligence.models.developer_behavior_models import (
    ActivityDistribution,
    DeveloperActivity,
    DeveloperBehaviorInsights,
    TestingHabits,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)

MINIMUM_EVENTS_FOR_PATTERNS = 5


class DeveloperBehaviorAnalyzer:
    """Analyze developer activities and sessions into behavioral insights."""

    def __init__(
        self,
        aggregator: ActivityAggregator | None = None,
        session_analyzer: ActivitySessionAnalyzer | None = None,
    ) -> None:
        self.aggregator = aggregator or ActivityAggregator()
        self.session_analyzer = session_analyzer or ActivitySessionAnalyzer()

    def analyze(
        self,
        activities: list[DeveloperActivity],
        metrics: ActivityMetrics | None = None,
        session_metrics: ActivitySessionMetrics | None = None,
        developer_id: str | None = None,
        project_path: str | None = None,
    ) -> DeveloperBehaviorInsights:
        """Analyze activity streams and session metrics into behavior patterns.

        Args:
            activities: List of DeveloperActivity events.
            metrics: Optional precomputed ActivityMetrics.
            session_metrics: Optional precomputed ActivitySessionMetrics.
            developer_id: Optional expected developer ID.
            project_path: Optional expected project path.

        Returns:
            DeveloperBehaviorInsights model instance.

        Raises:
            ValueError: If activity list has mismatched developers or projects.
            CustomException: If an unexpected calculation error occurs.
        """
        logger.info(
            "Starting developer behavior analysis | events=%d",
            len(activities),
        )

        if not activities:
            return DeveloperBehaviorInsights(
                developer_id=developer_id or "",
                project_path=project_path or "",
                total_events=0,
                total_sessions=0,
                total_active_duration_seconds=0.0,
                average_session_duration_seconds=0.0,
                events_per_hour=0.0,
                error_rate=0.0,
                ai_assistance_rate=0.0,
                files_touched_count=0,
                file_switching_rate=0.0,
                testing_habits=TestingHabits(),
                activity_distribution=ActivityDistribution(),
                identified_patterns=[
                    "Insufficient activity data for pattern recognition"
                ],
                has_sufficient_data=False,
            )

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
            # Calculate metrics if not supplied
            computed_metrics = metrics or self.aggregator.aggregate(activities)
            computed_session_metrics = session_metrics or self.session_analyzer.analyze(
                activities
            )

            total_events = len(activities)
            test_runs = computed_metrics.test_runs
            test_failures = computed_metrics.test_failures
            test_successes = computed_metrics.test_successes
            code_edits = computed_metrics.code_edits

            test_frequency = (
                round(test_runs / total_events, 4) if total_events > 0 else 0.0
            )
            test_failure_rate = (
                round(test_failures / test_runs, 4) if test_runs > 0 else 0.0
            )
            test_success_rate = (
                round(test_successes / test_runs, 4) if test_runs > 0 else 0.0
            )
            test_to_edit_ratio = (
                round(test_runs / max(code_edits, 1), 4)
                if code_edits > 0
                else (1.0 if test_runs > 0 else 0.0)
            )

            testing_habits = TestingHabits(
                test_frequency=test_frequency,
                test_failure_rate=test_failure_rate,
                test_success_rate=test_success_rate,
                test_to_edit_ratio=test_to_edit_ratio,
            )

            activity_distribution = ActivityDistribution(
                code_edits=computed_metrics.code_edits,
                file_opens=computed_metrics.file_opens,
                file_saves=computed_metrics.file_saves,
                test_runs=computed_metrics.test_runs,
                test_failures=computed_metrics.test_failures,
                test_successes=computed_metrics.test_successes,
                errors=computed_metrics.errors,
                ai_help_requests=computed_metrics.ai_help_requests,
            )

            error_rate = (
                round(computed_metrics.errors / total_events, 4)
                if total_events > 0
                else 0.0
            )
            ai_assistance_rate = (
                round(computed_metrics.ai_help_requests / total_events, 4)
                if total_events > 0
                else 0.0
            )
            file_switching_rate = (
                round(computed_metrics.files_touched / total_events, 4)
                if total_events > 0
                else 0.0
            )

            has_sufficient_data = total_events >= MINIMUM_EVENTS_FOR_PATTERNS
            identified_patterns = self._detect_patterns(
                total_events=total_events,
                computed_metrics=computed_metrics,
                testing_habits=testing_habits,
                error_rate=error_rate,
                ai_assistance_rate=ai_assistance_rate,
                file_switching_rate=file_switching_rate,
                session_metrics=computed_session_metrics,
            )

            insights = DeveloperBehaviorInsights(
                developer_id=first_dev_id,
                project_path=first_proj_path,
                total_events=total_events,
                total_sessions=computed_session_metrics.total_sessions,
                total_active_duration_seconds=computed_session_metrics.total_active_duration_seconds,
                average_session_duration_seconds=computed_session_metrics.average_session_duration_seconds,
                events_per_hour=computed_session_metrics.events_per_hour,
                error_rate=error_rate,
                ai_assistance_rate=ai_assistance_rate,
                files_touched_count=computed_metrics.files_touched,
                file_switching_rate=file_switching_rate,
                testing_habits=testing_habits,
                activity_distribution=activity_distribution,
                identified_patterns=identified_patterns,
                has_sufficient_data=has_sufficient_data,
            )

            logger.info(
                "Completed developer behavior analysis | dev=%s | patterns=%d",
                first_dev_id,
                len(identified_patterns),
            )
            return insights

        except ValueError:
            raise
        except Exception as error:
            logger.error("Failed during developer behavior analysis: %s", error)
            raise CustomException(error, sys) from error

    @staticmethod
    def _detect_patterns(
        total_events: int,
        computed_metrics: ActivityMetrics,
        testing_habits: TestingHabits,
        error_rate: float,
        ai_assistance_rate: float,
        file_switching_rate: float,
        session_metrics: ActivitySessionMetrics,
    ) -> list[str]:
        if total_events < MINIMUM_EVENTS_FOR_PATTERNS:
            return ["Insufficient activity data for pattern recognition"]

        patterns: list[str] = []

        # Testing patterns
        if (
            testing_habits.test_frequency >= 0.2
            or testing_habits.test_to_edit_ratio >= 0.5
        ):
            patterns.append("Test-driven development pattern observed")
        elif testing_habits.test_frequency < 0.05 and computed_metrics.code_edits >= 5:
            patterns.append("Infrequent testing pattern observed")

        if testing_habits.test_failure_rate >= 0.5 and computed_metrics.test_runs >= 3:
            patterns.append("Elevated test failure rate detected")

        # Error patterns
        if error_rate >= 0.25:
            patterns.append("Elevated error occurrence rate")

        # AI assistance patterns
        if ai_assistance_rate >= 0.2:
            patterns.append("Active utilization of AI assistance")

        # Context switching
        if file_switching_rate >= 0.5 and computed_metrics.files_touched >= 3:
            patterns.append("Broad file exploration pattern")
        elif file_switching_rate <= 0.25 and computed_metrics.files_touched <= 2:
            patterns.append("Focused single-context development")

        # Session habits
        if session_metrics.average_session_duration_seconds >= 1800:
            patterns.append("Sustained focus work sessions")
        elif (
            0 < session_metrics.average_session_duration_seconds < 600
            and session_metrics.total_sessions >= 2
        ):
            patterns.append("Short burst development sessions")

        if not patterns:
            patterns.append("Balanced general development pattern")

        return patterns
