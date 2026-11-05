from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionStatus(str, Enum):
    """Lifecycle status of a developer working session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    STALE = "stale"


class DeveloperProfile(BaseModel):
    """Developer identity profile model."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    name: str | None = None
    email: str | None = None
    created_at: datetime
    updated_at: datetime


class DeveloperRegistrationRequest(BaseModel):
    """Request payload for developer registration."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    developer_id: str | None = None


class DeveloperIdentificationRequest(BaseModel):
    """Request payload for resolving an existing developer identity."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str | None = None
    email: str | None = None


class DeveloperUpdateRequest(BaseModel):
    """Request payload for updating permitted developer profile fields."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None


class DeveloperSession(BaseModel):
    """Discrete developer working session model."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    developer_id: str
    status: str = SessionStatus.ACTIVE.value
    started_at: datetime
    last_activity_at: datetime
    ended_at: datetime | None = None
    project_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @property
    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE.value


class StartSessionRequest(BaseModel):
    """Request payload to initiate a new working session."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    project_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HeartbeatRequest(BaseModel):
    """Request payload to update active working session heartbeat."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    developer_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EndSessionRequest(BaseModel):
    """Request payload to conclude an active working session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    developer_id: str
    status: str = SessionStatus.COMPLETED.value


class SessionHistoryResponse(BaseModel):
    """Paginated collection of developer working sessions."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    total_count: int
    limit: int
    offset: int
    sessions: list[DeveloperSession] = Field(default_factory=list)
