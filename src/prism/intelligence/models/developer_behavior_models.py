from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeveloperActivity(BaseModel):
    """Represents a developer's activity within a project."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    developer_id: str
    event_type: str
    timestamp: datetime
    project_path: str
    file_path: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActivityDistribution(BaseModel):
    """Event count distribution across developer activity types."""

    model_config = ConfigDict(extra="forbid")

    code_edits: int = 0
    file_opens: int = 0
    file_saves: int = 0
    test_runs: int = 0
    test_failures: int = 0
    test_successes: int = 0
    errors: int = 0
    ai_help_requests: int = 0


class TestingHabits(BaseModel):
    """Testing metrics and habits for a developer."""

    __test__ = False
    model_config = ConfigDict(extra="forbid")

    test_frequency: float = 0.0
    test_failure_rate: float = 0.0
    test_success_rate: float = 0.0
    test_to_edit_ratio: float = 0.0


class DeveloperBehaviorInsights(BaseModel):
    """Comprehensive behavioral insights derived from developer activities and sessions."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    project_path: str
    total_events: int = 0
    total_sessions: int = 0
    total_active_duration_seconds: float = 0.0
    average_session_duration_seconds: float = 0.0
    events_per_hour: float = 0.0
    error_rate: float = 0.0
    ai_assistance_rate: float = 0.0
    files_touched_count: int = 0
    file_switching_rate: float = 0.0
    testing_habits: TestingHabits = Field(default_factory=TestingHabits)
    activity_distribution: ActivityDistribution = Field(
        default_factory=ActivityDistribution
    )
    identified_patterns: list[str] = Field(default_factory=list)
    has_sufficient_data: bool = False

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error
