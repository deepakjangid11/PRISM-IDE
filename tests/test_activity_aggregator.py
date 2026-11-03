from datetime import UTC, datetime

import pytest

from prism.intelligence.activity_aggregator import ActivityAggregator
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


def test_activity_aggregator_counts_events() -> None:
    activities = [
        make_activity("1", "code_edit", "src/main.py"),
        make_activity("2", "code_edit", "src/main.py"),
        make_activity("3", "file_open", "src/utils.py"),
        make_activity("4", "test_run"),
        make_activity("5", "test_failure"),
        make_activity("6", "test_success"),
        make_activity("7", "ai_help"),
        make_activity("8", "error"),
    ]

    metrics = ActivityAggregator().aggregate(activities)

    assert metrics.total_events == 8
    assert metrics.code_edits == 2
    assert metrics.file_opens == 1
    assert metrics.test_runs == 1
    assert metrics.test_failures == 1
    assert metrics.test_successes == 1
    assert metrics.ai_help_requests == 1
    assert metrics.errors == 1
    assert metrics.files_touched == 2


def test_activity_aggregator_rejects_empty_activity_list() -> None:
    with pytest.raises(ValueError, match="At least one activity"):
        ActivityAggregator().aggregate([])


def test_activity_aggregator_rejects_multiple_developers() -> None:
    activities = [
        make_activity("1", "code_edit", "src/main.py"),
        make_activity("2", "file_save", "src/main.py"),
    ]

    activities[1] = activities[1].model_copy(update={"developer_id": "developer-002"})

    with pytest.raises(
        ValueError,
        match="same developer and project",
    ):
        ActivityAggregator().aggregate(activities)


def test_activity_aggregator_counts_unique_files() -> None:
    activities = [
        make_activity("1", "code_edit", "src/main.py"),
        make_activity("2", "file_save", "src/main.py"),
        make_activity("3", "file_open", "src/utils.py"),
        make_activity("4", "test_run"),
    ]

    metrics = ActivityAggregator().aggregate(activities)

    assert metrics.files_touched == 2
