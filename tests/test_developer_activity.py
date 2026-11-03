from datetime import UTC, datetime

from prism.intelligence.developer_activity import ActivityRecorder
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)


def make_activity(
    event_id: str,
    event_type: str,
    file_path: str | None = None,
) -> DeveloperActivity:
    return DeveloperActivity(
        event_id=event_id,
        developer_id="developer-001",
        event_type=event_type,
        timestamp=datetime.now(UTC),
        project_path="/projects/sample",
        file_path=file_path,
    )


def test_activity_recorder_returns_recorded_activity() -> None:
    activity = make_activity(
        "event-001",
        "code_edit",
        "src/main.py",
    )

    recorder = ActivityRecorder()

    result = recorder.record(activity)

    assert result == activity


def test_activity_recorder_stores_activities() -> None:
    recorder = ActivityRecorder()

    first = make_activity("event-001", "code_edit", "src/main.py")
    second = make_activity("event-002", "file_save", "src/main.py")

    recorder.record(first)
    recorder.record(second)

    activities = recorder.get_activities()

    assert len(activities) == 2
    assert activities[0] == first
    assert activities[1] == second


def test_activity_recorder_returns_copy_of_activities() -> None:
    recorder = ActivityRecorder()

    activity = make_activity("event-001", "code_edit")

    recorder.record(activity)

    activities = recorder.get_activities()
    activities.clear()

    assert len(recorder.get_activities()) == 1


def test_activity_recorder_clear() -> None:
    recorder = ActivityRecorder()

    recorder.record(make_activity("event-001", "code_edit"))
    recorder.record(make_activity("event-002", "test_run"))

    recorder.clear()

    assert recorder.get_activities() == []
