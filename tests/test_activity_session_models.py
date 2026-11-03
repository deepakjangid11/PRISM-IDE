from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from prism.intelligence.models.activity_session_models import (
    ActivitySession,
    ActivitySessionMetrics,
)
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)


def test_activity_session_creation() -> None:
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 15, tzinfo=UTC)
    event1 = DeveloperActivity(
        event_id="e1",
        developer_id="dev1",
        event_type="code_edit",
        timestamp=t1,
        project_path="/test/project",
    )
    event2 = DeveloperActivity(
        event_id="e2",
        developer_id="dev1",
        event_type="file_save",
        timestamp=t2,
        project_path="/test/project",
    )

    session = ActivitySession(
        session_id="session_1",
        developer_id="dev1",
        project_path="/test/project",
        start_time=t1,
        end_time=t2,
        duration=timedelta(minutes=15),
        events=[event1, event2],
    )

    assert session.session_id == "session_1"
    assert session.developer_id == "dev1"
    assert session.project_path == "/test/project"
    assert session.start_time == t1
    assert session.end_time == t2
    assert session.duration == timedelta(minutes=15)
    assert session.event_count == 2
    assert session.active_duration == timedelta(minutes=15)
    assert session.session_start_time == t1
    assert session.session_end_time == t2
    assert session.duration_seconds == 900.0


def test_activity_session_getitem() -> None:
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 10, tzinfo=UTC)
    session = ActivitySession(
        session_id="session_1",
        developer_id="dev1",
        project_path="/test/project",
        start_time=t1,
        end_time=t2,
        duration=timedelta(minutes=10),
        events=[],
    )

    assert session["session_id"] == "session_1"
    assert session["session_start_time"] == t1
    assert session["session_end_time"] == t2
    assert session["active_duration"] == timedelta(minutes=10)
    assert session["event_count"] == 0

    with pytest.raises(KeyError):
        _ = session["invalid_key"]


def test_activity_session_extra_forbid() -> None:
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        ActivitySession(
            session_id="session_1",
            developer_id="dev1",
            project_path="/test/project",
            start_time=t1,
            end_time=t1,
            duration=timedelta(0),
            unknown_field="invalid",  # type: ignore[call-arg]
        )


def test_activity_session_metrics_creation_and_properties() -> None:
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)
    session = ActivitySession(
        session_id="session_1",
        developer_id="dev1",
        project_path="/test/project",
        start_time=t1,
        end_time=t2,
        duration=timedelta(hours=1),
        events=[],
    )

    metrics = ActivitySessionMetrics(
        developer_id="dev1",
        project_path="/test/project",
        first_activity_timestamp=t1,
        last_activity_timestamp=t2,
        total_sessions=1,
        total_events=6,
        total_active_duration=timedelta(hours=1),
        average_session_duration=timedelta(hours=1),
        longest_session_duration=timedelta(hours=1),
        average_events_per_hour=6.0,
        sessions=[session],
    )

    assert metrics.developer_id == "dev1"
    assert metrics.project_path == "/test/project"
    assert metrics.first_activity_timestamp == t1
    assert metrics.last_activity_timestamp == t2
    assert metrics.total_sessions == 1
    assert metrics.total_events == 6
    assert metrics.total_active_duration == timedelta(hours=1)
    assert metrics.average_session_duration == timedelta(hours=1)
    assert metrics.longest_session_duration == timedelta(hours=1)
    assert metrics.events_per_hour == 6.0
    assert metrics.total_active_duration_seconds == 3600.0
    assert metrics.average_session_duration_seconds == 3600.0
    assert metrics.longest_session_duration_seconds == 3600.0
    assert len(metrics.sessions) == 1


def test_activity_session_metrics_alias_events_per_hour() -> None:
    metrics = ActivitySessionMetrics(
        developer_id="dev1",
        project_path="/test/project",
        events_per_hour=4.5,  # type: ignore[call-arg]
    )
    assert metrics.average_events_per_hour == 4.5
    assert metrics.events_per_hour == 4.5


def test_activity_session_metrics_getitem() -> None:
    metrics = ActivitySessionMetrics(
        developer_id="dev1",
        project_path="/test/project",
        total_sessions=2,
        average_events_per_hour=5.0,
    )
    assert metrics["developer_id"] == "dev1"
    assert metrics["total_sessions"] == 2
    assert metrics["events_per_hour"] == 5.0
    assert metrics["average_events_per_hour"] == 5.0

    with pytest.raises(KeyError):
        _ = metrics["non_existent"]


def test_activity_session_metrics_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        ActivitySessionMetrics(
            developer_id="dev1",
            project_path="/test/project",
            random_key=123,  # type: ignore[call-arg]
        )
