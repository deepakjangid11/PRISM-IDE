import sys
from pathlib import Path

from prism.exceptions.custom_exception import CustomException
from prism.intelligence.developer_behavior_analyzer import (
    DeveloperBehaviorAnalyzer,
)
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.project_intelligence_models import (
    ProjectIntelligence,
)
from prism.intelligence.project_intelligence import build_project_intelligence
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.learning_path_generator import LearningPathGenerator
from prism.logging.logger import get_logger
from prism.mentoring.models import MentorContext, MentorMode, MentorRequest

logger = get_logger(__name__)


class MentorContextBuilder:
    """Compile rich multi-dimensional intelligence context for mentoring queries."""

    def __init__(
        self,
        skill_tracker: SkillTracker | None = None,
        behavior_analyzer: DeveloperBehaviorAnalyzer | None = None,
        gap_analyzer: KnowledgeGapAnalyzer | None = None,
        path_generator: LearningPathGenerator | None = None,
    ) -> None:
        self.skill_tracker = skill_tracker or SkillTracker()
        self.behavior_analyzer = behavior_analyzer or DeveloperBehaviorAnalyzer()
        self.gap_analyzer = gap_analyzer or KnowledgeGapAnalyzer()
        self.path_generator = path_generator or LearningPathGenerator()

    def build_context(
        self,
        request: MentorRequest,
        project_intelligence: ProjectIntelligence | None = None,
        activities: list[DeveloperActivity] | None = None,
    ) -> MentorContext:
        """Assemble context from project intelligence, behavior insights, skills, and gaps."""
        try:
            logger.info(
                "Building mentor context | dev=%s | mode=%s | query='%s'",
                request.developer_id,
                request.mode.value,
                request.query,
            )

            # 1. Project Intelligence
            proj_intel = project_intelligence
            if proj_intel is None and request.project_path:
                p = Path(request.project_path).expanduser()
                if p.exists() and p.is_dir():
                    raw_intel = build_project_intelligence(p)
                    if isinstance(raw_intel, ProjectIntelligence):
                        proj_intel = raw_intel

            # 2. Behavior Insights
            behavior_insights = None
            if activities:
                behavior_insights = self.behavior_analyzer.analyze(
                    activities,
                    developer_id=request.developer_id,
                    project_path=request.project_path,
                )

            # 3. Skill Profile
            skill_profile = self.skill_tracker.get_profile(request.developer_id)

            # 4. Learning Intelligence (Gaps & Path)
            knowledge_gaps = []
            learning_path = None
            target_skill = request.target_skill

            # If in learn mode and no explicit target skill, infer from query
            if not target_skill and request.mode == MentorMode.LEARN:
                for skill_name in self.gap_analyzer.skill_graph.get_skills():
                    if skill_name.lower() in request.query.lower():
                        target_skill = skill_name
                        break

            if target_skill:
                knowledge_gaps = self.gap_analyzer.identify_gaps(
                    skill_profile, target_skill
                )
                learning_path = self.path_generator.generate_path(
                    skill_profile, target_skill
                )

            context = MentorContext(
                developer_id=request.developer_id,
                mode=request.mode,
                query=request.query,
                project_intelligence=proj_intel,
                behavior_insights=behavior_insights,
                skill_profile=skill_profile,
                knowledge_gaps=knowledge_gaps,
                learning_path=learning_path,
            )

            logger.info("Successfully built mentor context")
            return context

        except Exception as error:
            logger.error("Failed building mentor context: %s", error)
            raise CustomException(error, sys) from error
