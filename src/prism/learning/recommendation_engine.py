import uuid

from prism.intelligence.models.skill_models import DeveloperSkillProfile
from prism.learning.models import (
    KnowledgeGap,
    KnowledgeGapType,
    LearningRecommendation,
    RecommendationPriority,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)


DIFFICULTY_EFFORT_MAP: dict[str, tuple[str, int]] = {
    "missing_prerequisite": ("intermediate", 15),
    "insufficient_evidence": ("beginner", 8),
    "low_proficiency": ("intermediate", 12),
    "weak_concept": ("intermediate", 10),
    "missing_framework": ("advanced", 20),
}


class LearningRecommendationEngine:
    """Generate structured, prioritized learning recommendations without duplicates."""

    def generate_recommendations(
        self,
        developer_profile: DeveloperSkillProfile,
        gaps: list[KnowledgeGap],
        target_role: str | None = None,
    ) -> list[LearningRecommendation]:
        """Produce deduplicated, explainable and prioritized recommendations from identified knowledge gaps."""
        dev_id = developer_profile.developer_id
        recommendations: list[LearningRecommendation] = []
        seen_skills: set[str] = set()

        # Sort gaps: HIGH severity first, then MISSING_PREREQUISITE before INSUFFICIENT_EVIDENCE
        sorted_gaps = sorted(
            gaps,
            key=lambda g: (
                0 if g.severity == "high" else 1,
                0 if g.gap_type == KnowledgeGapType.MISSING_PREREQUISITE else 1,
            ),
        )

        priority = 1
        for gap in sorted_gaps:
            skill = gap.missing_skill
            skill_key = skill.lower()
            if skill_key in seen_skills:
                continue
            seen_skills.add(skill_key)

            difficulty, effort = DIFFICULTY_EFFORT_MAP.get(
                gap.gap_type.value, ("intermediate", 10)
            )

            if (
                gap.severity == "high"
                and gap.gap_type == KnowledgeGapType.MISSING_PREREQUISITE
            ):
                priority_level = RecommendationPriority.CRITICAL.value
            elif gap.severity == "high":
                priority_level = RecommendationPriority.HIGH.value
            elif gap.gap_type == KnowledgeGapType.LOW_PROFICIENCY:
                priority_level = RecommendationPriority.MEDIUM.value
            else:
                priority_level = RecommendationPriority.LOW.value

            dev_skill = developer_profile.get_skill(skill)
            current_level = (
                dev_skill.proficiency_level.value if dev_skill else "insufficient_data"
            )

            role_context = f" for '{target_role}'" if target_role else ""

            if gap.gap_type == KnowledgeGapType.MISSING_PREREQUISITE:
                rec = LearningRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    developer_id=dev_id,
                    skill_name=skill,
                    title=f"Acquire Prerequisite: {skill}",
                    description=(
                        f"Foundational requirement '{skill}' is missing{role_context} "
                        f"(targeted toward '{gap.target_skill}'). Study core syntax and patterns."
                    ),
                    priority=priority,
                    priority_level=priority_level,
                    current_proficiency=current_level,
                    target_proficiency="intermediate",
                    difficulty=difficulty,
                    estimated_effort_hours=effort,
                    prerequisite_for=gap.target_skill
                    if skill != gap.target_skill
                    else None,
                    suggested_action=f"Build hands-on practice projects or tutorials using {skill}.",
                    reason=gap.importance_reason
                    or "Mandatory foundational prerequisite.",
                )
            elif gap.gap_type == KnowledgeGapType.LOW_PROFICIENCY:
                rec = LearningRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    developer_id=dev_id,
                    skill_name=skill,
                    title=f"Elevate Competence: {skill}",
                    description=(
                        f"Current competency in '{skill}' is elementary ({current_level}). "
                        f"Implement advanced patterns and test suites to reach intermediate mastery."
                    ),
                    priority=priority,
                    priority_level=priority_level,
                    current_proficiency=current_level,
                    target_proficiency="intermediate",
                    difficulty="intermediate",
                    estimated_effort_hours=12,
                    prerequisite_for=gap.target_skill
                    if skill != gap.target_skill
                    else None,
                    suggested_action=f"Build production-grade features and solve complex edge cases in {skill}.",
                    reason=gap.importance_reason
                    or "Current proficiency is below the required threshold.",
                )
            else:
                rec = LearningRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    developer_id=dev_id,
                    skill_name=skill,
                    title=f"Strengthen Evidence: {skill}",
                    description=(
                        f"Current evidence for '{skill}' is insufficient ({current_level}). "
                        "Write unit tests and build project features to demonstrate competence."
                    ),
                    priority=priority,
                    priority_level=priority_level,
                    current_proficiency=current_level,
                    target_proficiency="intermediate",
                    difficulty=difficulty,
                    estimated_effort_hours=effort,
                    prerequisite_for=gap.target_skill
                    if skill != gap.target_skill
                    else None,
                    suggested_action=f"Create verifiable test cases and code artifacts demonstrating {skill}.",
                    reason=gap.importance_reason
                    or "Need additional verifiable proof of competency.",
                )

            recommendations.append(rec)
            priority += 1

        logger.info(
            "Generated %d personalized recommendations for dev '%s'",
            len(recommendations),
            dev_id,
        )
        return recommendations
