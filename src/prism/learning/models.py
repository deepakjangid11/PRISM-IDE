from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeGapType(StrEnum):
    """Categorization of identified knowledge gaps."""

    MISSING_PREREQUISITE = "missing_prerequisite"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    LOW_PROFICIENCY = "low_proficiency"
    WEAK_CONCEPT = "weak_concept"
    MISSING_FRAMEWORK = "missing_framework"


class RecommendationPriority(StrEnum):
    """Priority level for personalized learning recommendations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KnowledgeGap(BaseModel):
    """Represents a gap in required skills, concepts, or prerequisites."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    developer_id: str
    target_skill: str
    missing_skill: str
    gap_type: KnowledgeGapType
    description: str
    severity: str = "medium"
    importance_reason: str | None = None

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class LearningRecommendation(BaseModel):
    """Structured and prioritized learning recommendation."""

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    developer_id: str
    skill_name: str
    title: str
    description: str
    priority: int = 1
    priority_level: str = RecommendationPriority.MEDIUM.value
    current_proficiency: str = "insufficient_data"
    target_proficiency: str = "intermediate"
    difficulty: str = "intermediate"
    estimated_effort_hours: int = 10
    prerequisite_for: str | None = None
    suggested_action: str
    reason: str | None = None

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class LearningPath(BaseModel):
    """Ordered sequence of learning steps to achieve a target technical skill or role."""

    model_config = ConfigDict(extra="forbid")

    path_id: str
    developer_id: str
    target_goal: str
    target_role: str | None = None
    steps: list[str]
    recommendations: list[LearningRecommendation] = Field(default_factory=list)
    estimated_steps: int = 0
    estimated_effort_hours: int = 0
    completed_steps: list[str] = Field(default_factory=list)

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class LearningProgress(BaseModel):
    """Tracks a developer's progress along a learning path."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    target_goal: str
    completed_skills: list[str] = Field(default_factory=list)
    in_progress_skills: list[str] = Field(default_factory=list)
    remaining_skills: list[str] = Field(default_factory=list)
    completion_percentage: float = 0.0

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error
