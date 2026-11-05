import uuid
from datetime import UTC, datetime

from prism.intelligence.models.developer_intelligence_models import (
    DeveloperInsight,
    DeveloperIntelligenceProfile,
    DeveloperPerformanceSnapshot,
    InsightCategory,
    InsightSeverity,
    IntelligenceAnalysisResult,
    SkillTrend,
    TrendDirection,
)
from prism.intelligence.models.skill_models import ProficiencyLevel
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.logging.logger import get_logger
from prism.storage.repositories.base import (
    ActivityRepository,
    IntelligenceRepository,
)

logger = get_logger(__name__)


class DeveloperIntelligenceEngine:
    """Centralized intelligence engine evaluating developer behavior, skills, trends, and gaps."""

    def __init__(
        self,
        skill_tracker: SkillTracker,
        gap_analyzer: KnowledgeGapAnalyzer,
        activity_repo: ActivityRepository | None = None,
        intelligence_repo: IntelligenceRepository | None = None,
    ) -> None:
        self.skill_tracker = skill_tracker
        self.gap_analyzer = gap_analyzer
        self.activity_repo = activity_repo
        self.intelligence_repo = intelligence_repo

    def analyze_developer(self, developer_id: str) -> IntelligenceAnalysisResult:
        """Run complete intelligence analysis generating insights, trends, and profile snapshot."""
        cleaned_id = developer_id.strip()
        if not cleaned_id:
            raise ValueError("Developer ID cannot be empty")

        now = datetime.now(UTC)
        logger.info("Executing intelligence analysis for developer '%s'", cleaned_id)

        # 1. Fetch Skill Profile
        profile = self.skill_tracker.get_profile(cleaned_id)
        skills = profile.skills

        # 2. Fetch Activity Stream
        activities = []
        if self.activity_repo is not None:
            activities = self.activity_repo.get_by_developer(cleaned_id)

        # Check for insufficient data
        total_activities = len(activities)
        total_skills = len(skills)
        has_sufficient_data = total_activities >= 3 or total_skills >= 2

        # 3. Analyze Trends across registered skills
        trends: list[SkillTrend] = []
        trends_map: dict[str, SkillTrend] = {}

        level_weights = {
            ProficiencyLevel.INSUFFICIENT_DATA: 0,
            ProficiencyLevel.BEGINNER: 1,
            ProficiencyLevel.ELEMENTARY: 2,
            ProficiencyLevel.INTERMEDIATE: 3,
            ProficiencyLevel.ADVANCED: 4,
            ProficiencyLevel.EXPERT: 5,
        }

        for skill_key, dev_skill in skills.items():
            name = dev_skill.skill_name
            count = dev_skill.evidence_count
            level = dev_skill.proficiency_level

            if count < 3:
                direction = TrendDirection.INSUFFICIENT_DATA
                desc = f"Observed {count} evidence point(s). Additional verified work required."
            elif level in (ProficiencyLevel.ADVANCED, ProficiencyLevel.EXPERT):
                direction = TrendDirection.IMPROVING
                desc = f"Strong competence verified across multiple projects with {count} evidence items."
            elif level == ProficiencyLevel.INTERMEDIATE:
                direction = TrendDirection.IMPROVING
                desc = f"Demonstrated consistent application with verified testing or features ({count} items)."
            else:
                direction = TrendDirection.STABLE
                desc = f"Foundational skill observed with {count} evidence points."

            prev_level = (
                ProficiencyLevel.BEGINNER.value
                if level_weights[level] > 1
                else ProficiencyLevel.INSUFFICIENT_DATA.value
            )
            growth_rate = round(min(1.0, count / 10.0), 2)

            trend = SkillTrend(
                skill_name=name,
                direction=direction,
                previous_level=prev_level,
                current_level=level.value,
                evidence_growth_rate=growth_rate,
                change_description=desc,
                confidence=dev_skill.confidence,
            )
            trends.append(trend)
            trends_map[name] = trend

        # 4. Generate Structured Insights
        insights: list[DeveloperInsight] = []

        # A. Strengths Insights
        if profile.strongest_skills:
            insights.append(
                DeveloperInsight(
                    insight_id=f"ins_str_{uuid.uuid4().hex[:8]}",
                    developer_id=cleaned_id,
                    category=InsightCategory.STRENGTH,
                    title="Core Technical Strengths Identified",
                    description=(
                        f"Demonstrated verified high proficiency in {', '.join(profile.strongest_skills[:3])}."
                    ),
                    severity=InsightSeverity.INFO,
                    evidence=[
                        f"High multi-project evidence verified for {s}"
                        for s in profile.strongest_skills[:3]
                    ],
                    supporting_skills=profile.strongest_skills[:3],
                    timestamp=now,
                    actionable_recommendation="Leverage core strengths to architect complex modules or mentor peers.",
                )
            )

        # B. Weaknesses Insights
        if profile.weakest_skills:
            insights.append(
                DeveloperInsight(
                    insight_id=f"ins_wk_{uuid.uuid4().hex[:8]}",
                    developer_id=cleaned_id,
                    category=InsightCategory.WEAKNESS,
                    title="Competencies Requiring Reinforcement",
                    description=(
                        f"Identified elementary or beginner proficiency in {', '.join(profile.weakest_skills[:3])}."
                    ),
                    severity=InsightSeverity.MEDIUM,
                    evidence=[
                        f"Limited activity depth observed for {s}"
                        for s in profile.weakest_skills[:3]
                    ],
                    supporting_skills=profile.weakest_skills[:3],
                    timestamp=now,
                    actionable_recommendation="Undertake targeted practical exercises to elevate competency baseline.",
                )
            )

        # C. Recurring Errors / Patterns from Activity Telemetry
        error_count = sum(
            1 for a in activities if a.event_type in ("syntax_error", "runtime_error")
        )
        if error_count >= 3:
            insights.append(
                DeveloperInsight(
                    insight_id=f"ins_err_{uuid.uuid4().hex[:8]}",
                    developer_id=cleaned_id,
                    category=InsightCategory.RECURRING_ERROR,
                    title="Recurring Execution or Syntax Errors Detected",
                    description=(
                        f"Observed {error_count} error events during recent working sessions."
                    ),
                    severity=InsightSeverity.HIGH
                    if error_count >= 6
                    else InsightSeverity.MEDIUM,
                    evidence=[
                        f"Recorded {error_count} syntax/runtime error events in telemetry"
                    ],
                    supporting_skills=[],
                    timestamp=now,
                    actionable_recommendation="Consider step-by-step debugging guidance and unit test validation before execution.",
                )
            )

        # D. Insufficient Data State Insight
        if not has_sufficient_data:
            insights.append(
                DeveloperInsight(
                    insight_id=f"ins_data_{uuid.uuid4().hex[:8]}",
                    developer_id=cleaned_id,
                    category=InsightCategory.GROWTH,
                    title="Initial Baseline Formation",
                    description="Insufficient activity telemetry to form definitive competency conclusions.",
                    severity=InsightSeverity.INFO,
                    evidence=["Telemetry events < 3 and verified skills < 2"],
                    supporting_skills=[],
                    timestamp=now,
                    actionable_recommendation="Engage in regular coding and feature development to establish skill footprint.",
                )
            )

        # 5. Detect Active Gaps across registered skills
        active_gaps_set: set[str] = set()
        for skill_key in list(skills.keys())[:5]:
            skill_name = skills[skill_key].skill_name
            gaps = self.gap_analyzer.identify_gaps(profile, skill_name)
            for g in gaps:
                active_gaps_set.add(g.missing_skill)

        # 6. Overall Status Assessment
        overall_status = "insufficient_data"
        if has_sufficient_data:
            avg_score = sum(s.proficiency_score for s in skills.values()) / max(
                1, len(skills)
            )
            if avg_score >= 70.0:
                overall_status = "excelling"
            elif error_count >= 5 and len(active_gaps_set) >= 3:
                overall_status = "struggling"
            elif len(active_gaps_set) > 0:
                overall_status = "learning"
            else:
                overall_status = "active"

        # 7. Create Performance Snapshot
        avg_score = (
            round(
                sum(s.proficiency_score for s in skills.values()) / max(1, len(skills)),
                1,
            )
            if skills
            else 0.0
        )
        consistency = round(min(1.0, len(activities) / 15.0), 2)

        snapshot = DeveloperPerformanceSnapshot(
            snapshot_id=f"snap_{uuid.uuid4().hex[:8]}",
            developer_id=cleaned_id,
            timestamp=now,
            total_activities=total_activities,
            verified_skills_count=total_skills,
            average_proficiency_score=avg_score,
            active_knowledge_gaps_count=len(active_gaps_set),
            tasks_completed_count=0,
            task_success_rate=1.0,
            learning_consistency_score=consistency,
            role_readiness_scores={},
        )

        intel_profile = DeveloperIntelligenceProfile(
            developer_id=cleaned_id,
            overall_status=overall_status,
            top_strengths=profile.strongest_skills,
            critical_weaknesses=profile.weakest_skills,
            active_gaps=sorted(active_gaps_set),
            trends=trends_map,
            recent_insights=insights,
            latest_snapshot=snapshot,
            has_sufficient_data=has_sufficient_data,
            last_updated=now,
        )

        result = IntelligenceAnalysisResult(
            analysis_id=f"res_{uuid.uuid4().hex[:8]}",
            developer_id=cleaned_id,
            profile=intel_profile,
            insights=insights,
            trends=trends,
            created_at=now,
        )

        # Persist to repository if available
        if self.intelligence_repo is not None:
            for ins in insights:
                self.intelligence_repo.save_insight(ins)
            self.intelligence_repo.save_snapshot(snapshot)

        return result

    def get_profile(self, developer_id: str) -> DeveloperIntelligenceProfile:
        """Retrieve latest profile or compute fresh analysis if none recorded."""
        result = self.analyze_developer(developer_id)
        return result.profile

    def get_insights(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperInsight]:
        """Fetch developer insights, falling back to on-demand analysis."""
        if self.intelligence_repo is not None:
            stored = self.intelligence_repo.get_insights(developer_id, limit, offset)
            if stored:
                return stored
        result = self.analyze_developer(developer_id)
        return result.insights[offset : offset + limit]

    def get_skill_trends(self, developer_id: str) -> list[SkillTrend]:
        """Fetch calculated skill velocity trends."""
        result = self.analyze_developer(developer_id)
        return result.trends
