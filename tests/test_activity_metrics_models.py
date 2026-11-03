import pytest
from pydantic import ValidationError

from prism.intelligence.models.activity_metrics_models import ActivityMetrics


def test_activity_metrics_creation() -> None:
    metrics = ActivityMetrics(
        developer_id="developer-001",
        project_path="/projects/sample",
        total_events=10,
        code_edits=3,
        file_opens=2,
        file_saves=2,
        test_runs=2,
        test_failures=1,
        test_successes=1,
        errors=1,
        ai_help_requests=1,
        files_touched=3,
    )

    assert metrics.developer_id == "developer-001"
    assert metrics.project_path == "/projects/sample"
    assert metrics.total_events == 10
    assert metrics.code_edits == 3
    assert metrics.test_failures == 1
    assert metrics.files_touched == 3


def test_activity_metrics_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ActivityMetrics(
            developer_id="developer-001",
            project_path="/projects/sample",
            total_events=10,
            code_edits=3,
            file_opens=2,
            file_saves=2,
            test_runs=2,
            test_failures=1,
            test_successes=1,
            errors=1,
            ai_help_requests=1,
            files_touched=3,
            unknown_metric=99,  # type: ignore[call-arg]
        )
