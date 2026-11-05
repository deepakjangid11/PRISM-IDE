import uuid

from prism.intelligence.models.skill_models import (
    DeveloperSkillProfile,
)
from prism.intelligence.skill_graph import SkillGraph, SkillGraphBuilder
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.models import LearningPath
from prism.learning.recommendation_engine import LearningRecommendationEngine
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class LearningPathGenerator:
    """Generate ordered, structured learning paths toward a target skill or role goal."""

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
        target_role: str | None = None,
    ) -> LearningPath:
        """Construct an ordered, prerequisite-respecting learning path skipping mastered skills."""
        cleaned_goal = target_goal.strip()
        if not cleaned_goal:
            raise ValueError("Target goal must be non-empty")

        dev_id = developer_profile.developer_id
        logger.info(
            "Generating learning path | dev=%s | goal=%s | role=%s",
            dev_id,
            cleaned_goal,
            target_role,
        )

        gaps = self.gap_analyzer.identify_gaps(developer_profile, cleaned_goal)
        recommendations = self.recommendation_engine.generate_recommendations(
            developer_profile, gaps, target_role=target_role
        )

        # Build ordered steps: all required skills in topological order
        prereqs = self.skill_graph.get_prerequisites(cleaned_goal, transitive=True)
        ordered_candidates = list(prereqs)
        if cleaned_goal not in ordered_candidates:
            ordered_candidates.append(cleaned_goal)

        # Filter out mastered skills (sufficient evidence present)
        steps: list[str] = []
        completed: list[str] = []
        for skill in ordered_candidates:
            dev_skill = developer_profile.get_skill(skill)
            if dev_skill is not None and dev_skill.has_sufficient_evidence:
                completed.append(skill)
            else:
                steps.append(skill)

        # If developer already mastered everything up to goal and goal itself, ensure goal is listed
        if not steps and cleaned_goal not in steps:
            steps.append(cleaned_goal)

        total_effort = len(steps) * 12

        path = LearningPath(
            path_id=str(uuid.uuid4()),
            developer_id=dev_id,
            target_goal=cleaned_goal,
            target_role=target_role,
            steps=steps,
            recommendations=recommendations,
            estimated_steps=len(steps),
            estimated_effort_hours=total_effort,
            completed_steps=completed,
        )

        logger.info(
            "Generated learning path with %d active steps (%d completed) for '%s'",
            len(steps),
            len(completed),
            cleaned_goal,
        )
        return path

    def generate_role_path(
        self,
        developer_profile: DeveloperSkillProfile,
        target_role: str,
    ) -> LearningPath:
        """Construct an ordered learning path covering all required skills for a target career role."""
        cleaned_role = target_role.strip()
        if not cleaned_role:
            raise ValueError("Target role must be non-empty")

        role_skills = self.skill_graph.get_role_skills(cleaned_role)
        if not role_skills:
            raise ValueError(f"Unknown target role: '{cleaned_role}'")

        # Collect all transitive prerequisites for all role skills
        all_required: set[str] = set()
        for s in role_skills:
            all_required.add(s)
            for p in self.skill_graph.get_prerequisites(s, transitive=True):
                all_required.add(p)

        ordered = self.skill_graph._topological_sort(all_required)

        # Filter out mastered skills
        steps: list[str] = []
        completed: list[str] = []
        for skill in ordered:
            dev_skill = developer_profile.get_skill(skill)
            if dev_skill is not None and dev_skill.has_sufficient_evidence:
                completed.append(skill)
            else:
                steps.append(skill)

        if not steps and role_skills:
            steps.append(role_skills[-1])

        gaps = self.gap_analyzer.identify_role_gaps(developer_profile, cleaned_role)
        recommendations = self.recommendation_engine.generate_recommendations(
            developer_profile, gaps, target_role=cleaned_role
        )

        return LearningPath(
            path_id=str(uuid.uuid4()),
            developer_id=developer_profile.developer_id,
            target_goal=f"Role: {cleaned_role}",
            target_role=cleaned_role,
            steps=steps,
            recommendations=recommendations,
            estimated_steps=len(steps),
            estimated_effort_hours=len(steps) * 12,
            completed_steps=completed,
        )
