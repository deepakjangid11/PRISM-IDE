from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.project_intelligence_models import (
    ProjectIntelligence,
)
from prism.logging.logger import get_logger
from prism.mentoring.context_builder import MentorContextBuilder
from prism.mentoring.models import MentorRequest, MentorResponse
from prism.mentoring.response_generator import (
    BaseMentorGenerator,
    DeterministicMentorGenerator,
)

logger = get_logger(__name__)


class MentoringEngine:
    """Core intelligence engine coordinating multi-modal developer mentoring."""

    def __init__(
        self,
        context_builder: MentorContextBuilder | None = None,
        generator: BaseMentorGenerator | None = None,
    ) -> None:
        self.context_builder = context_builder or MentorContextBuilder()
        self.generator = generator or DeterministicMentorGenerator()

    def mentor(
        self,
        request: MentorRequest,
        project_intelligence: ProjectIntelligence | None = None,
        activities: list[DeveloperActivity] | None = None,
    ) -> MentorResponse:
        """Process a developer mentoring request and return structured recommendations."""
        if not request.developer_id.strip():
            raise ValueError("Developer ID cannot be empty")
        if not request.query.strip():
            raise ValueError("Query cannot be empty")

        logger.info(
            "Mentoring engine processing request | dev=%s | mode=%s",
            request.developer_id,
            request.mode.value,
        )

        context = self.context_builder.build_context(
            request=request,
            project_intelligence=project_intelligence,
            activities=activities,
        )

        response = self.generator.generate(context)

        logger.info(
            "Mentoring engine generated response | recs=%d | steps=%d",
            len(response.recommendations),
            len(response.actionable_next_steps),
        )

        return response
