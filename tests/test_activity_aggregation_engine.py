from datetime import UTC, datetime, timedelta

from prism.intelligence.activity_aggregation_engine import (
    ActivityAggregationEngine,
)
from prism.intelligence.models.developer_behavior_models import DeveloperActivity


def test_aggregation_empty_list() -> None:
    aggregator = ActivityAggregationEngine()
    summary = aggregator.aggregate_summary([], developer_id="dev_empty")
    assert summary.total_activities == 0
    assert len(summary.categories) == 0
    assert len(summary.languages) == 0
    assert summary.error_frequency == 0.0


def test_aggregation_distributions_and_frequencies() -> None:
    aggregator = ActivityAggregationEngine()
    now = datetime.now(UTC)

    activities = [
        DeveloperActivity(
            event_id="e1",
            developer_id="dev_agg",
            event_type="file_edit",
            timestamp=now,
            project_path="/proj",
            metadata={
                "classification": {
                    "category": "coding",
                    "language": "Python",
                    "concept": "OOP",
                    "framework": "FastAPI",
                }
            },
        ),
        DeveloperActivity(
            event_id="e2",
            developer_id="dev_agg",
            event_type="test_run",
            timestamp=now,
            project_path="/proj",
            metadata={
                "classification": {
                    "category": "testing",
                    "language": "Python",
                    "concept": "Unit Testing",
                    "framework": "Pytest",
                }
            },
        ),
        DeveloperActivity(
            event_id="e3",
            developer_id="dev_agg",
            event_type="error",
            timestamp=now,
            project_path="/proj",
            metadata={
                "classification": {
                    "category": "debugging",
                    "language": "TypeScript",
                    "concept": "Exceptions",
                }
            },
        ),
        DeveloperActivity(
            event_id="e4",
            developer_id="dev_agg",
            event_type="refactor",
            timestamp=now,
            project_path="/proj",
            metadata={
                "classification": {
                    "category": "refactoring",
                    "language": "Go",
                    "concept": "Architecture",
                }
            },
        ),
    ]

    summary = aggregator.aggregate_summary(
        activities, developer_id="dev_agg", project_path="/proj"
    )
    assert summary.total_activities == 4
    assert len(summary.categories) == 4

    lang_dict = {l.language: l.count for l in summary.languages}
    assert lang_dict["Python"] == 2
    assert lang_dict["TypeScript"] == 1
    assert lang_dict["Go"] == 1

    assert summary.testing_frequency == 0.25
    assert summary.error_frequency == 0.25
    assert summary.debugging_frequency == 0.25
    assert summary.refactoring_frequency == 0.25


def test_aggregation_time_window_filtering() -> None:
    aggregator = ActivityAggregationEngine()
    now = datetime.now(UTC)

    activities = [
        DeveloperActivity(
            event_id="e_recent",
            developer_id="dev_time",
            event_type="file_edit",
            timestamp=now - timedelta(hours=2),
            project_path="/proj",
            metadata={"classification": {"category": "coding", "language": "Python"}},
        ),
        DeveloperActivity(
            event_id="e_old",
            developer_id="dev_time",
            event_type="file_edit",
            timestamp=now - timedelta(days=15),
            project_path="/proj",
            metadata={"classification": {"category": "coding", "language": "Java"}},
        ),
    ]

    summary_7d = aggregator.aggregate_summary(
        activities, developer_id="dev_time", time_window="7d"
    )
    assert summary_7d.total_activities == 1
    assert summary_7d.languages[0].language == "Python"

    summary_all = aggregator.aggregate_summary(
        activities, developer_id="dev_time", time_window="all"
    )
    assert summary_all.total_activities == 2
