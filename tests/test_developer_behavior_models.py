from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)


def test_developer_activity_creation() -> None:
    event = DeveloperActivity(
        event_id="event-001",
        developer_id="developer-001",
        event_type="code_edit",
        timestamp=datetime.now(UTC),
        project_path="/projects/sample",
        file_path="src/main.py",
        metadata={"line": 10},
    )

    assert event.event_id == "event-001"
    assert event.developer_id == "developer-001"
    assert event.event_type == "code_edit"
    assert event.file_path == "src/main.py"
    assert event.metadata["line"] == 10


def test_file_path_is_optional() -> None:
    event = DeveloperActivity(
        event_id="event-002",
        developer_id="developer-001",
        event_type="test_run",
        timestamp=datetime.now(UTC),
        project_path="/projects/sample",
    )

    assert event.file_path is None


def test_metadata_defaults_to_empty_dict() -> None:
    event = DeveloperActivity(
        event_id="event-003",
        developer_id="developer-001",
        event_type="file_open",
        timestamp=datetime.now(UTC),
        project_path="/projects/sample",
    )

    assert event.metadata == {}


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DeveloperActivity(
            event_id="event-004",
            developer_id="developer-001",
            event_type="file_save",
            timestamp=datetime.now(UTC),
            project_path="/projects/sample",
            unknown_field="not_allowed",  # type: ignore[call-arg]
        )
