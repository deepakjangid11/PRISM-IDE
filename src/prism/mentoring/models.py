from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from prism.intelligence.models.developer_behavior_models import (
    DeveloperBehaviorInsights,
)
from prism.intelligence.models.project_intelligence_models import (
    ProjectIntelligence,
)
from prism.intelligence.models.skill_models import DeveloperSkillProfile
from prism.learning.models import KnowledgeGap, LearningPath


class MentorMode(StrEnum):
    """Operational mode for the mentoring engine."""

    BUILD = "build"
    LEARN = "learn"


class MentorRequest(BaseModel):
    """Input request sent to the mentoring engine."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    mode: MentorMode
    query: str
    project_path: str | None = None
    target_skill: str | None = None
    context_metadata: dict[str, Any] = Field(default_factory=dict)


class MentorRecommendation(BaseModel):
    """Individual actionable mentoring recommendation."""

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    category: str
    title: str
    details: str
    actionable_steps: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class MentorContext(BaseModel):
    """Aggregated contextual intelligence compiled for a mentoring query."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    mode: MentorMode
    query: str
    project_intelligence: ProjectIntelligence | None = None
    behavior_insights: DeveloperBehaviorInsights | None = None
    skill_profile: DeveloperSkillProfile | None = None
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)
    learning_path: LearningPath | None = None

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class MentorResponse(BaseModel):
    """Structured, evidence-grounded response from the mentoring engine."""

    model_config = ConfigDict(extra="forbid")

    response_id: str
    developer_id: str
    mode: MentorMode
    summary: str
    explanation: str
    recommendations: list[MentorRecommendation] = Field(default_factory=list)
    actionable_next_steps: list[str] = Field(default_factory=list)
    context_used: dict[str, Any] = Field(default_factory=dict)

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error
