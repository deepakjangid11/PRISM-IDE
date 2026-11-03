from datetime import datetime, timedelta
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from prism.intelligence.models.developer_behavior_models import DeveloperActivity


class ActivitySession(BaseModel):
    """Represents a discrete session of developer activity."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    session_id: str
    developer_id: str
    project_path: str
    start_time: datetime
    end_time: datetime
    duration: timedelta
    events: list[DeveloperActivity] = Field(default_factory=list)

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def active_duration(self) -> timedelta:
        return self.duration

    @property
    def session_start_time(self) -> datetime:
        return self.start_time

    @property
    def session_end_time(self) -> datetime:
        return self.end_time

    @property
    def duration_seconds(self) -> float:
        return self.duration.total_seconds()

    def __getitem__(self, item: str) -> Any:
        if item == "session_start_time":
            return self.start_time
        if item == "session_end_time":
            return self.end_time
        if item == "active_duration":
            return self.duration
        if item == "event_count":
            return len(self.events)
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class ActivitySessionMetrics(BaseModel):
    """Aggregated time-based session metrics for developer activity."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    developer_id: str
    project_path: str
    first_activity_timestamp: datetime | None = None
    last_activity_timestamp: datetime | None = None
    total_sessions: int = 0
    total_events: int = 0
    total_active_duration: timedelta = Field(default_factory=timedelta)
    average_session_duration: timedelta = Field(default_factory=timedelta)
    longest_session_duration: timedelta = Field(default_factory=timedelta)
    average_events_per_hour: float = Field(
        default=0.0,
        validation_alias=AliasChoices("average_events_per_hour", "events_per_hour"),
    )
    sessions: list[ActivitySession] = Field(default_factory=list)

    @property
    def events_per_hour(self) -> float:
        return self.average_events_per_hour

    @property
    def total_active_duration_seconds(self) -> float:
        return self.total_active_duration.total_seconds()

    @property
    def average_session_duration_seconds(self) -> float:
        return self.average_session_duration.total_seconds()

    @property
    def longest_session_duration_seconds(self) -> float:
        return self.longest_session_duration.total_seconds()

    def __getitem__(self, item: str) -> Any:
        if item in ("events_per_hour", "average_events_per_hour"):
            return self.average_events_per_hour
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error
