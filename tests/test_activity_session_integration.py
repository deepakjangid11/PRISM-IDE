from datetime import UTC, datetime, timedelta

from prism.intelligence.activity_aggregator import ActivityAggregator
from prism.intelligence.activity_session_analyzer import (
    ActivitySessionAnalyzer,
)
from prism.intelligence.developer_activity import ActivityRecorder
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)


def test_developer_activity_end_to_end_pipeline() -> None:
    recorder = ActivityRecorder()
    aggregator = ActivityAggregator()
    session_analyzer = ActivitySessionAnalyzer()

    dev_id = "developer_alice"
    proj_path = "/workspace/prism-core"

    # Define a realistic work day with two coding sessions:
    # Morning session: 09:00 - 09:40 (40 mins active)
    t0 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    t1 = datetime(2026, 11, 3, 9, 5, tzinfo=UTC)
    t2 = datetime(2026, 11, 3, 9, 15, tzinfo=UTC)
    t3 = datetime(2026, 11, 3, 9, 40, tzinfo=UTC)

    # Lunch break / idle gap: 09:40 to 13:00 (3 hours 20 mins)

    # Afternoon session: 13:00 - 13:30 (30 mins active)
    t4 = datetime(2026, 11, 3, 13, 0, tzinfo=UTC)
    t5 = datetime(2026, 11, 3, 13, 10, tzinfo=UTC)
    t6 = datetime(2026, 11, 3, 13, 30, tzinfo=UTC)

    events_to_record = [
        DeveloperActivity(
            event_id="evt_1",
            developer_id=dev_id,
            event_type="file_open",
            timestamp=t0,
            project_path=proj_path,
            file_path="src/main.py",
        ),
        DeveloperActivity(
            event_id="evt_2",
            developer_id=dev_id,
            event_type="code_edit",
            timestamp=t1,
            project_path=proj_path,
            file_path="src/main.py",
        ),
        DeveloperActivity(
            event_id="evt_3",
            developer_id=dev_id,
            event_type="file_save",
            timestamp=t2,
            project_path=proj_path,
            file_path="src/main.py",
        ),
        DeveloperActivity(
            event_id="evt_4",
            developer_id=dev_id,
            event_type="test_run",
            timestamp=t3,
            project_path=proj_path,
            file_path="tests/test_main.py",
        ),
        DeveloperActivity(
            event_id="evt_5",
            developer_id=dev_id,
            event_type="code_edit",
            timestamp=t4,
            project_path=proj_path,
            file_path="src/utils.py",
        ),
        DeveloperActivity(
            event_id="evt_6",
            developer_id=dev_id,
            event_type="ai_help",
            timestamp=t5,
            project_path=proj_path,
            file_path="src/utils.py",
        ),
        DeveloperActivity(
            event_id="evt_7",
            developer_id=dev_id,
            event_type="test_success",
            timestamp=t6,
            project_path=proj_path,
            file_path="tests/test_utils.py",
        ),
    ]

    # Step 1: Record activities
    for event in events_to_record:
        recorded = recorder.record(event)
        assert recorded.event_id == event.event_id

    recorded_activities = recorder.get_activities()
    assert len(recorded_activities) == 7

    # Step 2: Feed into ActivityAggregator for count-based metrics
    metrics = aggregator.aggregate(recorded_activities)

    assert metrics.developer_id == dev_id
    assert metrics.project_path == proj_path
    assert metrics.total_events == 7
    assert metrics.file_opens == 1
    assert metrics.code_edits == 2
    assert metrics.file_saves == 1
    assert metrics.test_runs == 1
    assert metrics.test_successes == 1
    assert metrics.ai_help_requests == 1
    assert metrics.files_touched == 4  # main.py, test_main.py, utils.py, test_utils.py

    # Step 3: Feed into ActivitySessionAnalyzer for time-based session metrics
    session_metrics = session_analyzer.analyze(recorded_activities)

    assert session_metrics.developer_id == dev_id
    assert session_metrics.project_path == proj_path
    assert session_metrics.total_events == 7
    assert session_metrics.total_sessions == 2

    # Session 1 assertions
    s1 = session_metrics.sessions[0]
    assert s1.session_id == "session_1"
    assert s1.start_time == t0
    assert s1.end_time == t3
    assert s1.duration == timedelta(minutes=40)
    assert s1.event_count == 4

    # Session 2 assertions
    s2 = session_metrics.sessions[1]
    assert s2.session_id == "session_2"
    assert s2.start_time == t4
    assert s2.end_time == t6
    assert s2.duration == timedelta(minutes=30)
    assert s2.event_count == 3

    # Total active duration: 40m + 30m = 70m (1 hr 10 mins = 4200 seconds)
    # The 3h20m gap between 09:40 and 13:00 is correctly excluded!
    assert session_metrics.total_active_duration == timedelta(minutes=70)
    assert session_metrics.total_active_duration_seconds == 4200.0

    # Average session duration: 70m / 2 = 35m
    assert session_metrics.average_session_duration == timedelta(minutes=35)

    # Longest session duration: max(40m, 30m) = 40m
    assert session_metrics.longest_session_duration == timedelta(minutes=40)

    # Events per hour: 7 events / (70 / 60 hours) = 7 / 1.166667 = 6.0 events/hour
    assert session_metrics.average_events_per_hour == 6.0
    assert session_metrics.events_per_hour == 6.0

    # First and last activity timestamps
    assert session_metrics.first_activity_timestamp == t0
    assert session_metrics.last_activity_timestamp == t6

    # Verify recorder can still clear without impacting analyzed results
    recorder.clear()
    assert len(recorder.get_activities()) == 0
    assert len(session_metrics.sessions) == 2
