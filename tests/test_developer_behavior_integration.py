from datetime import UTC, datetime

from prism.intelligence.activity_aggregator import ActivityAggregator
from prism.intelligence.developer_activity import ActivityRecorder
from prism.intelligence.models.activity_metrics_models import ActivityMetrics
from prism.intelligence.models.developer_behavior_models import DeveloperActivity


def make_activity(
    event_id: str, event_type: str, file_path: str | None = None
) -> DeveloperActivity:
    return DeveloperActivity(
        event_id=event_id,
        developer_id="developer-001",
        event_type=event_type,
        timestamp=datetime.now(UTC),
        project_path="/projects/sample",
        file_path=file_path,
    )


def test_activity_recorder_to_aggregator_integration() -> None:
    recorder = ActivityRecorder()
    aggregator = ActivityAggregator()

    activities = [
        make_activity("event-001", "code_edit", "src/main.py"),
        make_activity("event-002", "file_open", "src/main.py"),
        make_activity("event-003", "file_save", "src/main.py"),
        make_activity("event-004", "test_run", "tests/test_main.py"),
        make_activity("event-005", "test_failure", "tests/test_main.py"),
        make_activity("event-006", "ai_help", "src/main.py"),
    ]

    for activity in activities:
        recorder.record(activity)

    recorded_activities = recorder.get_activities()

    metrics = aggregator.aggregate(recorded_activities)

    assert isinstance(metrics, ActivityMetrics)

    assert metrics.developer_id == "developer-001"
    assert metrics.project_path == "/projects/sample"

    assert metrics.total_events == 6
    assert metrics.code_edits == 1
    assert metrics.file_opens == 1
    assert metrics.file_saves == 1
    assert metrics.test_runs == 1
    assert metrics.test_failures == 1
    assert metrics.test_successes == 0
    assert metrics.errors == 0
    assert metrics.ai_help_requests == 1

    assert metrics.files_touched == 2
