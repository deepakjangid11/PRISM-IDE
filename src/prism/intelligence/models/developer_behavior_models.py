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
    metadata: dict[str, Any] = Field(default_factory=dict)
