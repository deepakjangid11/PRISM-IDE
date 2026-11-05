from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from prism.intelligence.developer_intelligence_engine import (
    DeveloperIntelligenceEngine,
)
from prism.intelligence.models.developer_intelligence_models import (
    DeveloperPerformanceSnapshot,
    SkillTrend,
    TaskStatus,
)
from prism.intelligence.models.skill_models import ProficiencyLevel
from prism.intelligence.skill_graph import SkillGraph
from prism.intelligence.skill_tracker import SkillTracker
from prism.logging.logger import get_logger
from prism.storage.repositories.base import (
    ActivityRepository,
    IntelligenceRepository,
    LearningRepository,
)

logger = get_logger(__name__)


# =========================================================================
# ANALYTICS RESPONSE MODELS
# =========================================================================


class RoleReadinessIndicator(BaseModel):
    """Evaluation of readiness toward a career role based on required skills."""

    model_config = ConfigDict(extra="forbid")

    role_name: str
    readiness_percentage: float
    mastered_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    is_ready: bool = False


class PerformanceOverview(BaseModel):
    """Holistic summary of developer performance, consistency, and velocity."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    overall_proficiency: str
    total_activities: int
    verified_skills_count: int
    average_proficiency_score: float
    active_knowledge_gaps: int
    task_completion_rate: float
    learning_consistency_score: float
    strongest_skills: list[str] = Field(default_factory=list)
    weakest_skills: list[str] = Field(default_factory=list)
    role_readiness: list[RoleReadinessIndicator] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillImprovementAnalytics(BaseModel):
    """Breakdown of skill improvements, regressions, and velocity trends."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    improving_skills: list[str] = Field(default_factory=list)
    stable_skills: list[str] = Field(default_factory=list)
    regressing_skills: list[str] = Field(default_factory=list)
    skills_with_insufficient_data: list[str] = Field(default_factory=list)
    trends: list[SkillTrend] = Field(default_factory=list)
    growth_velocity: float = 0.0


class LearningProgressAnalytics(BaseModel):
    """Analytics evaluating knowledge gap closure and roadmap progress."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    total_goals_tracked: int = 0
    average_completion_percentage: float = 0.0
    active_gaps_count: int = 0
    resolved_gaps_count: int = 0
    tasks_completed: int = 0
    tasks_in_progress: int = 0


# =========================================================================
# PERFORMANCE ANALYTICS SERVICE
# =========================================================================


class DeveloperPerformanceAnalytics:
    """Service generating actionable, empirical performance analytics."""

    def __init__(
        self,
        intelligence_engine: DeveloperIntelligenceEngine,
        skill_tracker: SkillTracker,
        skill_graph: SkillGraph,
        intelligence_repo: IntelligenceRepository | None = None,
        learning_repo: LearningRepository | None = None,
        activity_repo: ActivityRepository | None = None,
    ) -> None:
        self.intelligence_engine = intelligence_engine
        self.skill_tracker = skill_tracker
        self.skill_graph = skill_graph
        self.intelligence_repo = intelligence_repo
        self.learning_repo = learning_repo
        self.activity_repo = activity_repo

    def get_overview(self, developer_id: str) -> PerformanceOverview:
        """Calculate holistic developer performance overview."""
        cleaned_id = developer_id.strip()
        if not cleaned_id:
            raise ValueError("Developer ID cannot be empty")

        profile = self.skill_tracker.get_profile(cleaned_id)
        intel_profile = self.intelligence_engine.get_profile(cleaned_id)

        # 1. Activities & Tasks
        total_acts = 0
        if self.activity_repo is not None:
            total_acts = len(self.activity_repo.get_by_developer(cleaned_id))

        tasks = []
        if self.intelligence_repo is not None:
            tasks = self.intelligence_repo.get_tasks_for_developer(cleaned_id)

        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        task_completion_rate = (
            round(completed_tasks / max(1, len(tasks)), 2) if tasks else 1.0
        )

        # 2. Consistency & Average Score
        consistency = round(min(1.0, total_acts / 15.0), 2)
        avg_score = (
            round(
                sum(s.proficiency_score for s in profile.skills.values())
                / max(1, len(profile.skills)),
                1,
            )
            if profile.skills
            else 0.0
        )

        # 3. Role Readiness
        role_readiness_list: list[RoleReadinessIndicator] = []
        for role in self.skill_graph.get_roles():
            required = self.skill_graph.get_role_skills(role)
            if not required:
                continue

            mastered = []
            missing = []
            for r_skill in required:
                dev_skill = profile.get_skill(r_skill)
                if (
                    dev_skill is not None
                    and dev_skill.has_sufficient_evidence
                    and dev_skill.proficiency_level
                    in (
                        ProficiencyLevel.INTERMEDIATE,
                        ProficiencyLevel.ADVANCED,
                        ProficiencyLevel.EXPERT,
                    )
                ):
                    mastered.append(r_skill)
                else:
                    missing.append(r_skill)

            readiness_pct = round((len(mastered) / len(required)) * 100.0, 1)
            role_readiness_list.append(
                RoleReadinessIndicator(
                    role_name=role,
                    readiness_percentage=readiness_pct,
                    mastered_skills=mastered,
                    missing_skills=missing,
                    is_ready=readiness_pct >= 80.0,
                )
            )

        return PerformanceOverview(
            developer_id=cleaned_id,
            overall_proficiency=profile.overall_proficiency,
            total_activities=total_acts,
            verified_skills_count=len(profile.skills),
            average_proficiency_score=avg_score,
            active_knowledge_gaps=len(intel_profile.active_gaps),
            task_completion_rate=task_completion_rate,
            learning_consistency_score=consistency,
            strongest_skills=profile.strongest_skills,
            weakest_skills=profile.weakest_skills,
            role_readiness=role_readiness_list,
        )

    def get_skill_improvement(self, developer_id: str) -> SkillImprovementAnalytics:
        """Calculate skill velocity, improvements, and regressions."""
        cleaned_id = developer_id.strip()
        trends = self.intelligence_engine.get_skill_trends(cleaned_id)

        improving = [t.skill_name for t in trends if t.direction == "improving"]
        stable = [t.skill_name for t in trends if t.direction == "stable"]
        regressing = [t.skill_name for t in trends if t.direction == "regressing"]
        insufficient = [
            t.skill_name for t in trends if t.direction == "insufficient_data"
        ]

        avg_velocity = (
            round(sum(t.evidence_growth_rate for t in trends) / max(1, len(trends)), 2)
            if trends
            else 0.0
        )

        return SkillImprovementAnalytics(
            developer_id=cleaned_id,
            improving_skills=improving,
            stable_skills=stable,
            regressing_skills=regressing,
            skills_with_insufficient_data=insufficient,
            trends=trends,
            growth_velocity=avg_velocity,
        )

    def get_learning_progress(self, developer_id: str) -> LearningProgressAnalytics:
        """Calculate learning milestones and gap resolution progress."""
        cleaned_id = developer_id.strip()
        intel_profile = self.intelligence_engine.get_profile(cleaned_id)

        tasks = []
        if self.intelligence_repo is not None:
            tasks = self.intelligence_repo.get_tasks_for_developer(cleaned_id)

        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        in_progress_tasks = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)

        active_gaps = len(intel_profile.active_gaps)
        # Resolved gaps estimation based on verified skills matching graph prerequisites
        profile = self.skill_tracker.get_profile(cleaned_id)
        resolved_count = sum(
            1 for s in profile.skills.values() if s.has_sufficient_evidence
        )

        return LearningProgressAnalytics(
            developer_id=cleaned_id,
            total_goals_tracked=max(1, len(profile.skills)),
            average_completion_percentage=round(
                min(
                    100.0,
                    (resolved_count / max(1, resolved_count + active_gaps)) * 100.0,
                ),
                1,
            ),
            active_gaps_count=active_gaps,
            resolved_gaps_count=resolved_count,
            tasks_completed=completed_tasks,
            tasks_in_progress=in_progress_tasks,
        )

    def get_historical_snapshots(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperPerformanceSnapshot]:
        """Fetch historical performance checkpoint records."""
        if self.intelligence_repo is not None:
            return self.intelligence_repo.get_snapshots(developer_id, limit, offset)
        self.get_overview(developer_id)
        profile = self.intelligence_engine.get_profile(developer_id)
        return [profile.latest_snapshot] if profile.latest_snapshot else []
