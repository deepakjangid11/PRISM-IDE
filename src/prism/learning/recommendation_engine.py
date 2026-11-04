import uuid

from prism.intelligence.models.skill_models import DeveloperSkillProfile
from prism.learning.models import KnowledgeGap, KnowledgeGapType, LearningRecommendation
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class LearningRecommendationEngine:
    """Generate structured, prioritized learning recommendations without duplicates."""

    def generate_recommendations(
        self,
        developer_profile: DeveloperSkillProfile,
        gaps: list[KnowledgeGap],
    ) -> list[LearningRecommendation]:
        """Produce deduplicated and prioritized recommendations from identified knowledge gaps."""
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

            if gap.gap_type == KnowledgeGapType.MISSING_PREREQUISITE:
                rec = LearningRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    developer_id=dev_id,
                    skill_name=skill,
                    title=f"Acquire Prerequisite: {skill}",
                    description=(
                        f"Foundational requirement '{skill}' is missing for target '{gap.target_skill}'. "
                        "Study core concepts and complete introductory exercises."
                    ),
                    priority=priority,
                    prerequisite_for=gap.target_skill
                    if skill != gap.target_skill
                    else None,
                    suggested_action=f"Build hands-on practice projects or tutorials using {skill}.",
                )
            else:
                rec = LearningRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    developer_id=dev_id,
                    skill_name=skill,
                    title=f"Strengthen Evidence: {skill}",
                    description=(
                        f"Current evidence for '{skill}' is insufficient. "
                        "Write unit tests and build project features to demonstrate competence."
                    ),
                    priority=priority,
                    prerequisite_for=gap.target_skill
                    if skill != gap.target_skill
                    else None,
                    suggested_action=f"Create verifiable test cases and code artifacts demonstrating {skill}.",
                )

            recommendations.append(rec)
            priority += 1

        logger.info(
            "Generated %d learning recommendations for dev=%s",
            len(recommendations),
            dev_id,
        )
        return recommendations
