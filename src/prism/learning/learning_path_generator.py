import uuid

from prism.intelligence.models.skill_models import DeveloperSkillProfile
from prism.intelligence.skill_graph import SkillGraph, SkillGraphBuilder
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.models import LearningPath
from prism.learning.recommendation_engine import LearningRecommendationEngine
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class LearningPathGenerator:
    """Generate ordered, structured learning paths toward a target skill goal."""

    def __init__(
        self,
        skill_graph: SkillGraph | None = None,
        gap_analyzer: KnowledgeGapAnalyzer | None = None,
        recommendation_engine: LearningRecommendationEngine | None = None,
    ) -> None:
        self.skill_graph = skill_graph or SkillGraphBuilder.build_default_graph()
        self.gap_analyzer = gap_analyzer or KnowledgeGapAnalyzer(self.skill_graph)
        self.recommendation_engine = (
            recommendation_engine or LearningRecommendationEngine()
        )

    def generate_path(
        self,
        developer_profile: DeveloperSkillProfile,
        target_goal: str,
    ) -> LearningPath:
        """Construct an ordered, prerequisite-respecting learning path."""
        cleaned_goal = target_goal.strip()
        if not cleaned_goal:
            raise ValueError("Target goal must be non-empty")

        dev_id = developer_profile.developer_id
        logger.info(
            "Generating learning path | dev=%s | goal=%s",
            dev_id,
            cleaned_goal,
        )

        gaps = self.gap_analyzer.identify_gaps(developer_profile, cleaned_goal)
        recommendations = self.recommendation_engine.generate_recommendations(
            developer_profile, gaps
        )

        # Build ordered steps: all required skills in topological order
        prereqs = self.skill_graph.get_prerequisites(cleaned_goal, transitive=True)
        ordered_candidates = list(prereqs)
        if cleaned_goal not in ordered_candidates:
            ordered_candidates.append(cleaned_goal)

        # Filter to only skills that the developer has not yet mastered with sufficient evidence
        steps: list[str] = []
        for skill in ordered_candidates:
            dev_skill = developer_profile.get_skill(skill)
            if dev_skill is None or not dev_skill.has_sufficient_evidence:
                steps.append(skill)

        # If developer already mastered everything up to goal and goal itself, ensure goal is listed
        if not steps and cleaned_goal not in steps:
            steps.append(cleaned_goal)

        path = LearningPath(
            path_id=str(uuid.uuid4()),
            developer_id=dev_id,
            target_goal=cleaned_goal,
            steps=steps,
            recommendations=recommendations,
            estimated_steps=len(steps),
        )

        logger.info(
            "Generated learning path with %d steps for '%s'",
            len(steps),
            cleaned_goal,
        )
        return path
