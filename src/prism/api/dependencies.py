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
from prism.storage.bootstrap import check_db_connection
from prism.storage.database import get_session_factory
from prism.storage.repositories.base import (
    ActivityRepository,
    DeveloperRepository,
    LearningRepository,
    SkillGraphRepository,
    SkillRepository,
)
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryLearningRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
)
from prism.storage.repositories.mysql_activity_repo import (
    MySQLActivityRepository,
)
from prism.storage.repositories.mysql_developer_repo import (
    MySQLDeveloperRepository,
)
from prism.storage.repositories.mysql_graph_repo import MySQLSkillGraphRepository
from prism.storage.repositories.mysql_learning_repo import (
    MySQLLearningRepository,
)
from prism.storage.repositories.mysql_skill_repo import MySQLSkillRepository

# Storage layer repository wiring
developer_repo: DeveloperRepository
activity_repo: ActivityRepository
graph_repo: SkillGraphRepository
skill_repo: SkillRepository
learning_repo: LearningRepository

if check_db_connection():
    sf = get_session_factory()
    developer_repo = MySQLDeveloperRepository(sf)
    activity_repo = MySQLActivityRepository(sf, developer_repo=developer_repo)
    graph_repo = MySQLSkillGraphRepository(sf)
    skill_repo = MySQLSkillRepository(
        sf, developer_repo=developer_repo, graph_repo=graph_repo
    )
    learning_repo = MySQLLearningRepository(
        sf, developer_repo=developer_repo, graph_repo=graph_repo
    )
else:
    developer_repo = InMemoryDeveloperRepository()
    activity_repo = InMemoryActivityRepository(dev_repo=developer_repo)
    graph_repo = InMemorySkillGraphRepository()
    skill_repo = InMemorySkillRepository(dev_repo=developer_repo, graph_repo=graph_repo)
    learning_repo = InMemoryLearningRepository(
        dev_repo=developer_repo, graph_repo=graph_repo
    )

# Shared singleton instances across API routes
skill_graph = SkillGraphBuilder.build_default_graph(repository=graph_repo)
skill_tracker = SkillTracker(repository=skill_repo, developer_repo=developer_repo)
behavior_analyzer = DeveloperBehaviorAnalyzer()
gap_analyzer = KnowledgeGapAnalyzer(skill_graph=skill_graph)
rec_engine = LearningRecommendationEngine()
path_generator = LearningPathGenerator(
    skill_graph=skill_graph,
    gap_analyzer=gap_analyzer,
    recommendation_engine=rec_engine,
)
progress_tracker = LearningProgressTracker(repository=learning_repo)
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
