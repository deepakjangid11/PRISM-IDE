from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# =========================================================================
# INTELLIGENCE ENUMS
# =========================================================================


class InsightCategory(StrEnum):
    """Categorization for developer intelligence insights."""

    STRENGTH = "strength"
    WEAKNESS = "weakness"
    PATTERN = "pattern"
    GAP = "gap"
    RECURRING_ERROR = "recurring_error"
    GROWTH = "growth"


class InsightSeverity(StrEnum):
    """Severity or importance level of an insight."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrendDirection(StrEnum):
    """Direction of skill proficiency over time."""

    IMPROVING = "improving"
    REGRESSING = "regressing"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


class TaskDifficulty(StrEnum):
    """Difficulty level assigned to a personalized task."""

    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TaskPriority(StrEnum):
    """Priority level for task recommendation."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(StrEnum):
    """Lifecycle status of a personalized learning task."""

    GENERATED = "generated"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class FeedbackCategory(StrEnum):
    """Category classification of automated developer feedback."""

    POSITIVE = "positive"
    IMPROVEMENT_REQUIRED = "improvement_required"
    KNOWLEDGE_GAP = "knowledge_gap"
    PERFORMANCE_WARNING = "performance_warning"
    MILESTONE_ACHIEVED = "milestone_achieved"


class LearningStrategyType(StrEnum):
    """Pedagogical adaptation strategy."""

    STANDARD = "standard"
    PREREQUISITE_FIRST = "prerequisite_first"
    PRACTICE_INTENSIVE = "practice_intensive"
    ACCELERATED = "accelerated"
    REMEDIATION = "remediation"


# =========================================================================
# DEVELOPER INTELLIGENCE & INSIGHT MODELS
# =========================================================================


class IntelligenceEvidence(BaseModel):
    """Traceable, verifiable evidence supporting an intelligence insight."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source: str
    description: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeveloperInsight(BaseModel):
    """Structured insight derived from developer behavior, activities, and skills."""

    model_config = ConfigDict(extra="forbid")

    insight_id: str
    developer_id: str
    category: InsightCategory
    title: str
    description: str
    severity: InsightSeverity = InsightSeverity.INFO
    evidence: list[str] = Field(default_factory=list)
    supporting_skills: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actionable_recommendation: str | None = None

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class SkillTrend(BaseModel):
    """Observed velocity and direction of a developer's specific skill."""

    model_config = ConfigDict(extra="forbid")

    skill_name: str
    direction: TrendDirection
    previous_level: str
    current_level: str
    evidence_growth_rate: float = 0.0
    change_description: str
    confidence: float = 1.0


class DeveloperPerformanceSnapshot(BaseModel):
    """Historical checkpoint of developer performance metrics."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    developer_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_activities: int = 0
    verified_skills_count: int = 0
    average_proficiency_score: float = 0.0
    active_knowledge_gaps_count: int = 0
    tasks_completed_count: int = 0
    task_success_rate: float = 0.0
    learning_consistency_score: float = 0.0
    role_readiness_scores: dict[str, float] = Field(default_factory=dict)

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class DeveloperIntelligenceProfile(BaseModel):
    """Centralized high-level intelligence assessment of a developer."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    overall_status: str = "insufficient_data"
    top_strengths: list[str] = Field(default_factory=list)
    critical_weaknesses: list[str] = Field(default_factory=list)
    active_gaps: list[str] = Field(default_factory=list)
    trends: dict[str, SkillTrend] = Field(default_factory=dict)
    recent_insights: list[DeveloperInsight] = Field(default_factory=list)
    latest_snapshot: DeveloperPerformanceSnapshot | None = None
    has_sufficient_data: bool = False
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class IntelligenceAnalysisResult(BaseModel):
    """Result of an on-demand or periodic intelligence refresh."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    developer_id: str
    profile: DeveloperIntelligenceProfile
    insights: list[DeveloperInsight] = Field(default_factory=list)
    trends: list[SkillTrend] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# =========================================================================
# PERSONALIZED TASK MODELS
# =========================================================================


class PersonalizedTask(BaseModel):
    """Actionable development task recommended to bridge skill gaps."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    developer_id: str
    title: str
    description: str
    target_skill: str
    difficulty: TaskDifficulty
    priority: TaskPriority
    status: TaskStatus = TaskStatus.GENERATED
    estimated_minutes: int = 30
    target_role: str | None = None
    prerequisite_skills: list[str] = Field(default_factory=list)
    reason: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    problem_statement: str | None = None
    learning_objectives: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    expected_deliverables: list[str] = Field(default_factory=list)
    evaluation_criteria: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class TaskRecommendation(BaseModel):
    """Recommended task with urgency score and readiness justification."""

    model_config = ConfigDict(extra="forbid")

    task: PersonalizedTask
    importance_score: float = 1.0
    readiness_assessment: str


class TaskProgress(BaseModel):
    """Status update payload for a personalized task."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    status: TaskStatus
    notes: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskOutcome(BaseModel):
    """Execution outcome logged for a personalized task."""

    model_config = ConfigDict(extra="forbid")

    outcome_id: str
    task_id: str
    developer_id: str
    success: bool
    execution_notes: str
    verified_artifacts: list[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskEvaluation(BaseModel):
    """Automated assessment of task completion and evidence generation."""

    model_config = ConfigDict(extra="forbid")

    evaluation_id: str
    task_id: str
    developer_id: str
    passed: bool
    score: float
    strengths_demonstrated: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    generated_evidence_id: str | None = None
    feedback_message: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# =========================================================================
# INTELLIGENT FEEDBACK MODELS
# =========================================================================


class DeveloperFeedback(BaseModel):
    """Targeted, evidence-backed feedback delivered to a developer."""

    model_config = ConfigDict(extra="forbid")

    feedback_id: str
    developer_id: str
    related_task_id: str | None = None
    related_skill: str | None = None
    category: FeedbackCategory
    message: str
    supporting_evidence: list[str] = Field(default_factory=list)
    recommended_next_action: str
    confidence_level: float = 1.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


# =========================================================================
# LEARNING ADAPTATION MODELS
# =========================================================================


class LearningAdaptation(BaseModel):
    """Recorded adaptation adjusting learning strategy or difficulty."""

    model_config = ConfigDict(extra="forbid")

    adaptation_id: str
    developer_id: str
    previous_strategy: str
    new_strategy: LearningStrategyType
    adaptation_reason: str
    adjusted_difficulty: TaskDifficulty
    adjusted_priorities: dict[str, str] = Field(default_factory=dict)
    stalled_skills_detected: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error
