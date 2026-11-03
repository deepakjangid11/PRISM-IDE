from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from prism.exceptions.custom_exception import CustomException
from prism.intelligence.activity_session_analyzer import (
    ActivitySessionAnalyzer,
)
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)


def make_activity(
    event_id: str,
    timestamp: datetime,
    developer_id: str = "dev_1",
    project_path: str = "/workspace/prism",
    event_type: str = "code_edit",
    file_path: str | None = "src/main.py",
) -> DeveloperActivity:
    return DeveloperActivity(
        event_id=event_id,
        developer_id=developer_id,
        event_type=event_type,
        timestamp=timestamp,
        project_path=project_path,
        file_path=file_path,
    )


def test_edge_case_1_empty_activity_input() -> None:
    analyzer = ActivitySessionAnalyzer()
    metrics = analyzer.analyze([])

    assert metrics.total_sessions == 0
    assert metrics.total_events == 0
    assert metrics.total_active_duration == timedelta(0)
    assert metrics.average_session_duration == timedelta(0)
    assert metrics.longest_session_duration == timedelta(0)
    assert metrics.average_events_per_hour == 0.0
    assert metrics.sessions == []
    assert metrics.first_activity_timestamp is None
    assert metrics.last_activity_timestamp is None
    assert metrics.developer_id == ""
    assert metrics.project_path == ""


def test_edge_case_1_empty_input_with_context() -> None:
    analyzer = ActivitySessionAnalyzer()
    metrics = analyzer.analyze(
        [], developer_id="dev_special", project_path="/workspace/custom"
    )
    assert metrics.developer_id == "dev_special"
    assert metrics.project_path == "/workspace/custom"
    assert metrics.total_sessions == 0


def test_edge_case_2_single_activity_event() -> None:
    analyzer = ActivitySessionAnalyzer()
    t = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)
    activity = make_activity("e1", t)

    metrics = analyzer.analyze([activity])

    assert metrics.total_sessions == 1
    assert metrics.total_events == 1
    assert metrics.first_activity_timestamp == t
    assert metrics.last_activity_timestamp == t
    assert metrics.total_active_duration == timedelta(0)
    assert metrics.average_session_duration == timedelta(0)
    assert metrics.longest_session_duration == timedelta(0)
    assert metrics.average_events_per_hour == 0.0
    assert len(metrics.sessions) == 1

    session = metrics.sessions[0]
    assert session.session_id == "session_1"
    assert session.start_time == t
    assert session.end_time == t
    assert session.duration == timedelta(0)
    assert session.event_count == 1
    assert session.events == [activity]


def test_edge_case_3_multiple_events_in_one_session() -> None:
    analyzer = ActivitySessionAnalyzer()
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 10, tzinfo=UTC)
    t3 = datetime(2026, 11, 3, 9, 25, tzinfo=UTC)

    activities = [
        make_activity("e1", t1, event_type="code_edit"),
        make_activity("e2", t2, event_type="file_save"),
        make_activity("e3", t3, event_type="test_run"),
    ]

    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 1
    assert metrics.total_events == 3
    assert metrics.first_activity_timestamp == t1
    assert metrics.last_activity_timestamp == t3
    assert metrics.total_active_duration == timedelta(minutes=25)
    assert metrics.average_session_duration == timedelta(minutes=25)
    assert metrics.longest_session_duration == timedelta(minutes=25)
    assert len(metrics.sessions) == 1

    session = metrics.sessions[0]
    assert session.duration == timedelta(minutes=25)
    assert session.event_count == 3


def test_edge_case_4_multiple_separate_sessions() -> None:
    analyzer = ActivitySessionAnalyzer()
    # Session 1: 09:00 - 09:15 (15 min)
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 15, tzinfo=UTC)
    # Gap: 45 min (> 30 min)
    # Session 2: 10:00 - 10:30 (30 min)
    t3 = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)
    t4 = datetime(2026, 11, 3, 10, 30, tzinfo=UTC)

    activities = [
        make_activity("e1", t1),
        make_activity("e2", t2),
        make_activity("e3", t3),
        make_activity("e4", t4),
    ]

    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 2
    assert metrics.total_events == 4
    assert metrics.first_activity_timestamp == t1
    assert metrics.last_activity_timestamp == t4
    # Active duration = 15m + 30m = 45m (gap of 45m excluded)
    assert metrics.total_active_duration == timedelta(minutes=45)
    assert metrics.average_session_duration == timedelta(minutes=22, seconds=30)
    assert metrics.longest_session_duration == timedelta(minutes=30)


def test_edge_case_5_exact_30_minute_inactivity_boundary() -> None:
    analyzer = ActivitySessionAnalyzer()
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 30, tzinfo=UTC)  # exactly 30 min gap

    activities = [make_activity("e1", t1), make_activity("e2", t2)]
    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 1
    assert metrics.sessions[0].duration == timedelta(minutes=30)
    assert metrics.total_active_duration == timedelta(minutes=30)


def test_edge_case_6_more_than_30_minute_inactivity_gap() -> None:
    analyzer = ActivitySessionAnalyzer()
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 30, 1, tzinfo=UTC)  # 30 min + 1 second gap

    activities = [make_activity("e1", t1), make_activity("e2", t2)]
    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 2
    assert metrics.sessions[0].duration == timedelta(0)
    assert metrics.sessions[1].duration == timedelta(0)
    assert metrics.total_active_duration == timedelta(0)


def test_edge_case_7_out_of_chronological_order() -> None:
    analyzer = ActivitySessionAnalyzer()
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 10, tzinfo=UTC)
    t3 = datetime(2026, 11, 3, 9, 20, tzinfo=UTC)

    # Provide in reverse order
    activities = [
        make_activity("e3", t3),
        make_activity("e1", t1),
        make_activity("e2", t2),
    ]

    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 1
    assert metrics.first_activity_timestamp == t1
    assert metrics.last_activity_timestamp == t3
    assert metrics.total_active_duration == timedelta(minutes=20)
    assert [e.event_id for e in metrics.sessions[0].events] == [
        "e1",
        "e2",
        "e3",
    ]


def test_edge_case_8_duplicate_timestamps() -> None:
    analyzer = ActivitySessionAnalyzer()
    t = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)

    activities = [
        make_activity("e1", t, event_type="code_edit"),
        make_activity("e2", t, event_type="file_save"),
        make_activity("e3", t, event_type="test_run"),
    ]

    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 1
    assert metrics.total_events == 3
    assert metrics.sessions[0].duration == timedelta(0)
    assert metrics.total_active_duration == timedelta(0)
    assert metrics.average_events_per_hour == 0.0


def test_edge_case_9_different_developers_raises_value_error() -> None:
    analyzer = ActivitySessionAnalyzer()
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 5, tzinfo=UTC)

    activities = [
        make_activity("e1", t1, developer_id="alice"),
        make_activity("e2", t2, developer_id="bob"),
    ]

    with pytest.raises(
        ValueError,
        match="All activities must belong to the same developer and project",
    ):
        analyzer.analyze(activities)


def test_edge_case_10_different_projects_raises_value_error() -> None:
    analyzer = ActivitySessionAnalyzer()
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 5, tzinfo=UTC)

    activities = [
        make_activity("e1", t1, project_path="/workspace/proj1"),
        make_activity("e2", t2, project_path="/workspace/proj2"),
    ]

    with pytest.raises(
        ValueError,
        match="All activities must belong to the same developer and project",
    ):
        analyzer.analyze(activities)


def test_edge_case_11_timezone_aware_and_mixed_timestamps() -> None:
    analyzer = ActivitySessionAnalyzer()
    # UTC+2 11:00 is equal to UTC 09:00
    tz_plus_2 = timezone(timedelta(hours=2))
    t1 = datetime(2026, 11, 3, 11, 0, tzinfo=tz_plus_2)
    # UTC 09:15 is 15 minutes after t1
    t2 = datetime(2026, 11, 3, 9, 15, tzinfo=UTC)
    # Naive timestamp (interpreted as UTC) 09:25 is 10 minutes after t2
    t3 = datetime(2026, 11, 3, 9, 25)

    activities = [
        make_activity("e1", t1),
        make_activity("e2", t2),
        make_activity("e3", t3),
    ]

    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 1
    assert metrics.total_events == 3
    assert metrics.total_active_duration == timedelta(minutes=25)


def test_edge_case_12_correct_active_duration_excluding_idle() -> None:
    analyzer = ActivitySessionAnalyzer()
    # 09:00 -> 09:05 -> 09:10 = 10 min active
    # 10:00 -> code_edit (0 min active)
    # 50 min idle excluded
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 5, tzinfo=UTC)
    t3 = datetime(2026, 11, 3, 9, 10, tzinfo=UTC)
    t4 = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)

    activities = [
        make_activity("e1", t1),
        make_activity("e2", t2),
        make_activity("e3", t3),
        make_activity("e4", t4),
    ]

    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 2
    assert metrics.sessions[0].duration == timedelta(minutes=10)
    assert metrics.sessions[1].duration == timedelta(0)
    assert metrics.total_active_duration == timedelta(minutes=10)


def test_edge_case_13_correct_average_session_duration() -> None:
    analyzer = ActivitySessionAnalyzer()
    # Session 1: 10 min
    t1 = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 8, 10, tzinfo=UTC)
    # Session 2: 20 min
    t3 = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)
    t4 = datetime(2026, 11, 3, 10, 20, tzinfo=UTC)
    # Session 3: 30 min
    t5 = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
    t6 = datetime(2026, 11, 3, 12, 30, tzinfo=UTC)

    activities = [
        make_activity("e1", t1),
        make_activity("e2", t2),
        make_activity("e3", t3),
        make_activity("e4", t4),
        make_activity("e5", t5),
        make_activity("e6", t6),
    ]

    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 3
    assert metrics.total_active_duration == timedelta(minutes=60)
    # Average = 60 min / 3 = 20 min
    assert metrics.average_session_duration == timedelta(minutes=20)


def test_edge_case_14_correct_longest_session_duration() -> None:
    analyzer = ActivitySessionAnalyzer()
    # Session 1: 5 min
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 5, tzinfo=UTC)
    # Session 2: 45 min
    t3 = datetime(2026, 11, 3, 11, 0, tzinfo=UTC)
    t4 = datetime(2026, 11, 3, 11, 20, tzinfo=UTC)
    t5 = datetime(2026, 11, 3, 11, 45, tzinfo=UTC)

    activities = [
        make_activity("e1", t1),
        make_activity("e2", t2),
        make_activity("e3", t3),
        make_activity("e4", t4),
        make_activity("e5", t5),
    ]

    metrics = analyzer.analyze(activities)

    assert metrics.total_sessions == 2
    assert metrics.longest_session_duration == timedelta(minutes=45)


def test_edge_case_15_correct_events_per_hour() -> None:
    analyzer = ActivitySessionAnalyzer()
    # 4 events spanning 30 minutes active duration
    # 30 min = 0.5 hours
    # 4 events / 0.5 hours = 8.00 events/hour
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 10, tzinfo=UTC)
    t3 = datetime(2026, 11, 3, 9, 20, tzinfo=UTC)
    t4 = datetime(2026, 11, 3, 9, 30, tzinfo=UTC)

    activities = [
        make_activity("e1", t1),
        make_activity("e2", t2),
        make_activity("e3", t3),
        make_activity("e4", t4),
    ]

    metrics = analyzer.analyze(activities)

    assert metrics.total_active_duration == timedelta(minutes=30)
    assert metrics.average_events_per_hour == 8.0
    assert metrics.events_per_hour == 8.0


def test_custom_inactivity_threshold_override() -> None:
    # Set threshold to 10 minutes
    analyzer = ActivitySessionAnalyzer(
        default_inactivity_threshold=timedelta(minutes=10)
    )
    t1 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 15, tzinfo=UTC)  # 15 min gap (> 10m)

    activities = [make_activity("e1", t1), make_activity("e2", t2)]

    # Uses default 10m threshold -> splits into 2 sessions
    metrics = analyzer.analyze(activities)
    assert metrics.total_sessions == 2

    # Override dynamically to 20m threshold -> stays 1 session
    metrics2 = analyzer.analyze(activities, inactivity_threshold=timedelta(minutes=20))
    assert metrics2.total_sessions == 1


def test_explicit_developer_id_mismatch_raises_value_error() -> None:
    analyzer = ActivitySessionAnalyzer()
    t = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    activities = [make_activity("e1", t, developer_id="dev_1")]
    with pytest.raises(
        ValueError,
        match="All activities must belong to the same developer and project",
    ):
        analyzer.analyze(activities, developer_id="dev_2")


def test_explicit_project_path_mismatch_raises_value_error() -> None:
    analyzer = ActivitySessionAnalyzer()
    t = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    activities = [make_activity("e1", t, project_path="/workspace/proj1")]
    with pytest.raises(
        ValueError,
        match="All activities must belong to the same developer and project",
    ):
        analyzer.analyze(activities, project_path="/workspace/proj2")


def test_unexpected_exception_raises_custom_exception() -> None:
    analyzer = ActivitySessionAnalyzer()
    t = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    activities = [make_activity("e1", t)]
    with (
        patch(
            "prism.intelligence.activity_session_analyzer.sorted",
            side_effect=RuntimeError("Unexpected error"),
        ),
        pytest.raises(CustomException),
    ):
        analyzer.analyze(activities)
