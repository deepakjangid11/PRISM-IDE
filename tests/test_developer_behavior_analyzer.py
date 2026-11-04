from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from prism.exceptions.custom_exception import CustomException
from prism.intelligence.developer_behavior_analyzer import (
    DeveloperBehaviorAnalyzer,
)
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
    DeveloperBehaviorInsights,
)


def make_event(
    event_id: str,
    event_type: str,
    timestamp: datetime,
    file_path: str = "src/main.py",
    developer_id: str = "dev1",
    project_path: str = "/projects/p1",
) -> DeveloperActivity:
    return DeveloperActivity(
        event_id=event_id,
        developer_id=developer_id,
        event_type=event_type,
        timestamp=timestamp,
        project_path=project_path,
        file_path=file_path,
    )


def test_empty_activities_returns_default_insights() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    insights = analyzer.analyze([], developer_id="dev1", project_path="/p1")

    assert insights.developer_id == "dev1"
    assert insights.project_path == "/p1"
    assert insights.total_events == 0
    assert not insights.has_sufficient_data
    assert (
        "Insufficient activity data for pattern recognition"
        in insights.identified_patterns
    )
    assert insights.error_rate == 0.0
    assert insights.ai_assistance_rate == 0.0


def test_insufficient_data_under_threshold() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    t0 = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    events = [
        make_event("e1", "code_edit", t0),
        make_event("e2", "file_save", t0 + timedelta(minutes=1)),
    ]
    insights = analyzer.analyze(events)

    assert insights.total_events == 2
    assert not insights.has_sufficient_data
    assert (
        "Insufficient activity data for pattern recognition"
        in insights.identified_patterns
    )


def test_test_driven_development_pattern_detected() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    t0 = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    events = [
        make_event("e1", "code_edit", t0 + timedelta(minutes=1)),
        make_event("e2", "test_run", t0 + timedelta(minutes=2)),
        make_event("e3", "test_success", t0 + timedelta(minutes=3)),
        make_event("e4", "code_edit", t0 + timedelta(minutes=4)),
        make_event("e5", "test_run", t0 + timedelta(minutes=5)),
        make_event("e6", "test_success", t0 + timedelta(minutes=6)),
    ]
    insights = analyzer.analyze(events)

    assert insights.has_sufficient_data
    assert "Test-driven development pattern observed" in insights.identified_patterns
    assert insights.testing_habits.test_frequency > 0.2


def test_elevated_test_failures_pattern_detected() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    t0 = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    events = [
        make_event("e1", "test_run", t0 + timedelta(minutes=1)),
        make_event("e2", "test_failure", t0 + timedelta(minutes=2)),
        make_event("e3", "test_run", t0 + timedelta(minutes=3)),
        make_event("e4", "test_failure", t0 + timedelta(minutes=4)),
        make_event("e5", "test_run", t0 + timedelta(minutes=5)),
        make_event("e6", "test_failure", t0 + timedelta(minutes=6)),
    ]
    insights = analyzer.analyze(events)

    assert insights.has_sufficient_data
    assert "Elevated test failure rate detected" in insights.identified_patterns
    assert insights.testing_habits.test_failure_rate == 1.0


def test_ai_assistance_and_errors_detected() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    t0 = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    events = [
        make_event("e1", "error", t0 + timedelta(minutes=1)),
        make_event("e2", "ai_help", t0 + timedelta(minutes=2)),
        make_event("e3", "error", t0 + timedelta(minutes=3)),
        make_event("e4", "ai_help", t0 + timedelta(minutes=4)),
        make_event("e5", "code_edit", t0 + timedelta(minutes=5)),
    ]
    insights = analyzer.analyze(events)

    assert insights.has_sufficient_data
    assert "Elevated error occurrence rate" in insights.identified_patterns
    assert "Active utilization of AI assistance" in insights.identified_patterns


def test_broad_file_exploration_detected() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    t0 = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    events = [
        make_event("e1", "file_open", t0 + timedelta(minutes=1), file_path="a.py"),
        make_event("e2", "file_open", t0 + timedelta(minutes=2), file_path="b.py"),
        make_event("e3", "file_open", t0 + timedelta(minutes=3), file_path="c.py"),
        make_event("e4", "file_open", t0 + timedelta(minutes=4), file_path="d.py"),
        make_event("e5", "file_open", t0 + timedelta(minutes=5), file_path="e.py"),
    ]
    insights = analyzer.analyze(events)

    assert insights.has_sufficient_data
    assert "Broad file exploration pattern" in insights.identified_patterns
    assert insights.files_touched_count == 5


def test_focused_single_context_detected() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    t0 = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    events = [
        make_event(
            f"e{i}", "code_edit", t0 + timedelta(minutes=i), file_path="single.py"
        )
        for i in range(1, 9)
    ]
    insights = analyzer.analyze(events)

    assert insights.has_sufficient_data
    assert "Focused single-context development" in insights.identified_patterns


def test_developer_and_project_mismatch_raises_value_error() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    t0 = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    events1 = [
        make_event("e1", "code_edit", t0, developer_id="dev1"),
        make_event("e2", "code_edit", t0 + timedelta(minutes=1), developer_id="dev2"),
    ]
    with pytest.raises(ValueError, match="same developer and project"):
        analyzer.analyze(events1)

    events2 = [
        make_event("e1", "code_edit", t0, project_path="/p1"),
        make_event("e2", "code_edit", t0 + timedelta(minutes=1), project_path="/p2"),
    ]
    with pytest.raises(ValueError, match="same developer and project"):
        analyzer.analyze(events2)


def test_explicit_argument_mismatch_raises_value_error() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    t0 = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    events = [
        make_event("e1", "code_edit", t0, developer_id="dev1", project_path="/p1")
    ]

    with pytest.raises(ValueError, match="same developer and project"):
        analyzer.analyze(events, developer_id="different_dev")

    with pytest.raises(ValueError, match="same developer and project"):
        analyzer.analyze(events, project_path="/different_path")


def test_unexpected_exception_raises_custom_exception() -> None:
    analyzer = DeveloperBehaviorAnalyzer()
    t0 = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    events = [make_event("e1", "code_edit", t0)]
    with (
        patch.object(
            analyzer.aggregator,
            "aggregate",
            side_effect=RuntimeError("Aggregator exploded"),
        ),
        pytest.raises(CustomException),
    ):
        analyzer.analyze(events)


def test_behavior_insights_getitem_and_extra_fields() -> None:
    insights = DeveloperBehaviorInsights(
        developer_id="dev1",
        project_path="/p1",
        total_events=10,
    )
    assert insights["developer_id"] == "dev1"
    assert insights["total_events"] == 10

    with pytest.raises(KeyError):
        _ = insights["unknown_key"]

    with pytest.raises(ValidationError):
        DeveloperBehaviorInsights(
            developer_id="dev1",
            project_path="/p1",
            extra_field=123,  # type: ignore[call-arg]
        )
