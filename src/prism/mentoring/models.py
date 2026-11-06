from datetime import UTC, datetime
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


# =========================================================================
# ADAPTIVE MENTORING MODELS (PHASE 19)
# =========================================================================


class MentoringStrategy(StrEnum):
    """Dynamic instructional strategy selected for adaptive mentoring."""

    CONCEPTUAL_EXPLANATION = "conceptual_explanation"
    GUIDED_IMPLEMENTATION = "guided_implementation"
    STEP_BY_STEP_LEARNING = "step_by_step_learning"
    DEBUGGING_GUIDANCE = "debugging_guidance"
    PRACTICAL_EXERCISE = "practical_exercise"
    ADVANCED_TECHNICAL_GUIDANCE = "advanced_technical_guidance"


class AdaptiveMentorRequest(BaseModel):
    """Developer request for adaptive, level-tailored mentoring."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    query: str
    project_path: str | None = None
    target_skill: str | None = None
    preferred_strategy: MentoringStrategy | None = None
    context_metadata: dict[str, Any] = Field(default_factory=dict)
    use_llm: bool = True
    enable_rag: bool = True


class AdaptiveMentorResponse(BaseModel):
    """Adaptive mentoring response tailored to developer proficiency and context."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    developer_id: str
    selected_strategy: MentoringStrategy
    explanation_complexity: str
    mentoring_difficulty: str
    summary: str
    explanation: str
    actionable_steps: list[str] = Field(default_factory=list)
    targeted_knowledge_gaps: list[str] = Field(default_factory=list)
    recommended_tasks: list[str] = Field(default_factory=list)
    retrieved_citations: list[str] = Field(default_factory=list)
    provider_used: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class MentoringSessionRecord(BaseModel):
    """Persisted record of an adaptive mentoring interaction."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    developer_id: str
    strategy: MentoringStrategy
    query: str
    target_skill: str | None = None
    summary: str
    outcome_rating: float | None = None
    outcome_notes: str | None = None
    provider_used: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class MentoringEffectiveness(BaseModel):
    """Aggregated effectiveness analytics for developer mentoring interactions."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    total_sessions: int = 0
    average_rating: float = 0.0
    strategy_distribution: dict[str, int] = Field(default_factory=dict)
    skill_improvements_correlated: int = 0
    effectiveness_score: float = 0.0
