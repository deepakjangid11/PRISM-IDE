from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActivityCategory(StrEnum):
    """Categorization of developer activities."""

    CODING = "coding"
    DEBUGGING = "debugging"
    TESTING = "testing"
    REFACTORING = "refactoring"
    ARCHITECTURE = "architecture"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    DEPENDENCY = "dependency"
    GENERAL = "general"


class ProgrammingLanguage(StrEnum):
    """Supported canonical programming languages."""

    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    JAVA = "Java"
    CSHARP = "C#"
    GO = "Go"
    RUST = "Rust"
    CPP = "C++"
    C = "C"
    PHP = "PHP"
    RUBY = "Ruby"
    KOTLIN = "Kotlin"
    SWIFT = "Swift"
    DART = "Dart"
    SQL = "SQL"
    HTML = "HTML"
    CSS = "CSS"
    R = "R"
    JULIA = "Julia"
    UNKNOWN = "Unknown"


class ActivityClassification(BaseModel):
    """Enriched semantic classification of a developer activity event."""

    model_config = ConfigDict(extra="forbid")

    category: ActivityCategory = ActivityCategory.GENERAL
    language: str = ProgrammingLanguage.UNKNOWN.value
    framework: str | None = None
    concept: str = "General Programming"
    subconcept: str | None = None
    related_skill: str | None = None
    project_component: str | None = None
    complexity_estimate: str = "medium"  # low, medium, high
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)


class ActivityIngestRequest(BaseModel):
    """Request payload to ingest and classify a developer activity."""

    model_config = ConfigDict(extra="forbid")

    event_id: str | None = None
    developer_id: str
    event_type: str
    project_path: str
    file_path: str | None = None
    session_id: str | None = None
    code_snippet: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchActivityIngestRequest(BaseModel):
    """Request payload for batch activity ingestion."""

    model_config = ConfigDict(extra="forbid")

    activities: list[ActivityIngestRequest] = Field(default_factory=list)


class ActivityResponse(BaseModel):
    """Enriched activity response with classification and session metadata."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    developer_id: str
    session_id: str | None = None
    event_type: str
    timestamp: datetime
    project_path: str
    file_path: str | None = None
    classification: ActivityClassification
    metadata: dict[str, Any] = Field(default_factory=dict)


class LanguageDistributionItem(BaseModel):
    """Language activity count and share percentage."""

    model_config = ConfigDict(extra="forbid")

    language: str
    count: int
    percentage: float


class FrameworkDistributionItem(BaseModel):
    """Framework activity count and share percentage."""

    model_config = ConfigDict(extra="forbid")

    framework: str
    count: int
    percentage: float


class ConceptDistributionItem(BaseModel):
    """Concept activity count and share percentage."""

    model_config = ConfigDict(extra="forbid")

    concept: str
    count: int
    percentage: float


class CategoryDistributionItem(BaseModel):
    """Category activity count and share percentage."""

    model_config = ConfigDict(extra="forbid")

    category: str
    count: int
    percentage: float


class ActivitySummaryResponse(BaseModel):
    """Aggregated activity summary metrics."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    project_path: str | None = None
    total_activities: int
    categories: list[CategoryDistributionItem] = Field(default_factory=list)
    languages: list[LanguageDistributionItem] = Field(default_factory=list)
    frameworks: list[FrameworkDistributionItem] = Field(default_factory=list)
    concepts: list[ConceptDistributionItem] = Field(default_factory=list)
    error_frequency: float = 0.0
    debugging_frequency: float = 0.0
    testing_frequency: float = 0.0
    refactoring_frequency: float = 0.0
    time_window: str = "all"


class PaginatedActivityResponse(BaseModel):
    """Paginated collection of enriched activities."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    total_count: int
    limit: int
    offset: int
    activities: list[ActivityResponse] = Field(default_factory=list)
