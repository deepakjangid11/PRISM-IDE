from prism.intelligence.developer_behavior_analyzer import (
    DeveloperBehaviorAnalyzer,
)
from prism.intelligence.skill_graph import SkillGraphBuilder
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.learning_path_generator import LearningPathGenerator
from prism.learning.progress_tracker import LearningProgressTracker
from prism.learning.recommendation_engine import LearningRecommendationEngine
from prism.mentoring.context_builder import MentorContextBuilder
from prism.mentoring.engine import MentoringEngine
from prism.mentoring.response_generator import DeterministicMentorGenerator

# Shared singleton instances across API routes
skill_graph = SkillGraphBuilder.build_default_graph()
skill_tracker = SkillTracker()
behavior_analyzer = DeveloperBehaviorAnalyzer()
gap_analyzer = KnowledgeGapAnalyzer(skill_graph=skill_graph)
rec_engine = LearningRecommendationEngine()
path_generator = LearningPathGenerator(
    skill_graph=skill_graph,
    gap_analyzer=gap_analyzer,
    recommendation_engine=rec_engine,
)
progress_tracker = LearningProgressTracker()
context_builder = MentorContextBuilder(
    skill_tracker=skill_tracker,
    behavior_analyzer=behavior_analyzer,
    gap_analyzer=gap_analyzer,
    path_generator=path_generator,
)
mentor_generator = DeterministicMentorGenerator()
mentoring_engine = MentoringEngine(
    context_builder=context_builder,
    generator=mentor_generator,
)
