from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeGapType(StrEnum):
    """Categorization of identified knowledge gaps."""

    MISSING_PREREQUISITE = "missing_prerequisite"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    LOW_PROFICIENCY = "low_proficiency"


class KnowledgeGap(BaseModel):
    """Represents a gap in required skills or prerequisites."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    developer_id: str
    target_skill: str
    missing_skill: str
    gap_type: KnowledgeGapType
    description: str
    severity: str = "medium"

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
    prerequisite_for: str | None = None
    suggested_action: str

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class LearningPath(BaseModel):
    """Ordered sequence of learning steps to achieve a target technical skill."""

    model_config = ConfigDict(extra="forbid")

    path_id: str
    developer_id: str
    target_goal: str
    steps: list[str]
    recommendations: list[LearningRecommendation] = Field(default_factory=list)
    estimated_steps: int = 0

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
