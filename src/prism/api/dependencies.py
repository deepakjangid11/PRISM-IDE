from prism.config.settings import settings
from prism.intelligence.activity_intelligence_service import (
    DeveloperActivityIntelligenceService,
)
from prism.intelligence.developer_activity import ActivityRecorder
from prism.intelligence.developer_behavior_analyzer import (
    DeveloperBehaviorAnalyzer,
)
from prism.intelligence.developer_identity import DeveloperIdentityService
from prism.intelligence.developer_session import DeveloperSessionService
from prism.intelligence.skill_evidence_engine import SkillEvidenceEngine
from prism.intelligence.skill_graph import SkillGraph, SkillGraphBuilder
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.learning_path_generator import LearningPathGenerator
from prism.learning.progress_tracker import LearningProgressTracker
from prism.learning.recommendation_engine import LearningRecommendationEngine
from prism.logging.logger import get_logger
from prism.mentoring.context_builder import MentorContextBuilder
from prism.mentoring.engine import MentoringEngine
from prism.mentoring.response_generator import DeterministicMentorGenerator
from prism.storage.bootstrap import check_db_connection
from prism.storage.database import get_session_factory
from prism.storage.repositories.base import (
    ActivityRepository,
    DeveloperRepository,
    DeveloperSessionRepository,
    LearningRepository,
    SkillGraphRepository,
    SkillRepository,
)
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryLearningRepository,
    InMemorySessionRepository,
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
from prism.storage.repositories.mysql_session_repo import MySQLSessionRepository
from prism.storage.repositories.mysql_skill_repo import MySQLSkillRepository

logger = get_logger(__name__)


def init_storage_repositories(
    backend: str | None = None,
) -> tuple[
    DeveloperRepository,
    ActivityRepository,
    SkillGraphRepository,
    SkillRepository,
    LearningRepository,
    DeveloperSessionRepository,
]:
    """Initialize repository layer based on explicit configuration.

    In 'mysql' mode, verifies connectivity and fails with a clear RuntimeError if
    MySQL is unreachable. Never silently falls back to in-memory storage.
    In 'memory' mode, explicitly provisions in-memory repository instances.
    """
    selected_backend = (backend or settings.storage_backend).strip().lower()

    if selected_backend == "memory":
        logger.info("Storage layer explicitly configured with 'memory' backend")
        mem_dev = InMemoryDeveloperRepository()
        mem_act = InMemoryActivityRepository(dev_repo=mem_dev)
        mem_grp = InMemorySkillGraphRepository()
        mem_skl = InMemorySkillRepository(dev_repo=mem_dev, graph_repo=mem_grp)
        mem_lrn = InMemoryLearningRepository(dev_repo=mem_dev, graph_repo=mem_grp)
        mem_ses = InMemorySessionRepository(dev_repo=mem_dev)
        return mem_dev, mem_act, mem_grp, mem_skl, mem_lrn, mem_ses

    if selected_backend == "mysql":
        if not check_db_connection():
            error_msg = (
                f"CRITICAL: Failed to connect to MySQL database at "
                f"{settings.db_host}:{settings.db_port}/{settings.db_name}. "
                "Silent in-memory fallback is disabled for production safety. "
                "Ensure MySQL Server 8.0+ is running or explicitly configure "
                "STORAGE_BACKEND=memory for isolated testing."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        sf = get_session_factory()
        sql_dev = MySQLDeveloperRepository(sf)
        sql_act = MySQLActivityRepository(sf, developer_repo=sql_dev)
        sql_grp = MySQLSkillGraphRepository(sf)
        sql_skl = MySQLSkillRepository(sf, developer_repo=sql_dev, graph_repo=sql_grp)
        sql_lrn = MySQLLearningRepository(
            sf, developer_repo=sql_dev, graph_repo=sql_grp
        )
        sql_ses = MySQLSessionRepository(sf, developer_repo=sql_dev)
        return sql_dev, sql_act, sql_grp, sql_skl, sql_lrn, sql_ses

    raise ValueError(
        f"Unsupported storage backend '{selected_backend}'. Expected 'mysql' or 'memory'."
    )


# Storage layer repository wiring
(
    developer_repo,
    activity_repo,
    graph_repo,
    skill_repo,
    learning_repo,
    session_repo,
) = init_storage_repositories()

# Developer identity and session services
identity_service = DeveloperIdentityService(developer_repo=developer_repo)
session_service = DeveloperSessionService(
    session_repo=session_repo,
    developer_repo=developer_repo,
    app_settings=settings,
)

# Activity recorder service wired to persistent repository and session service
activity_recorder = ActivityRecorder(
    repository=activity_repo,
    session_service=session_service,
)

# Multi-language Developer Activity Intelligence service
activity_intelligence_service = DeveloperActivityIntelligenceService(
    activity_repo=activity_repo,
    session_service=session_service,
)

# Skill graph initialization:
# In MySQL mode, loads existing persistent graph topology without re-inserting on startup.
# In Memory mode, populates the default curriculum graph for testing.
if settings.storage_backend.strip().lower() == "mysql":
    skill_graph = SkillGraph(repository=graph_repo)
else:
    skill_graph = SkillGraphBuilder.build_default_graph(repository=graph_repo)

# Shared singleton instances across API routes
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
    activity_recorder=activity_recorder,
)
mentor_generator = DeterministicMentorGenerator()
mentoring_engine = MentoringEngine(
    context_builder=context_builder,
    generator=mentor_generator,
)

# Skill Evidence Engine instance
skill_evidence_engine = SkillEvidenceEngine(skill_tracker=skill_tracker)


def get_skill_tracker() -> SkillTracker:
    return skill_tracker


def get_skill_evidence_engine() -> SkillEvidenceEngine:
    return skill_evidence_engine


def get_skill_graph() -> SkillGraph:
    return skill_graph


def get_gap_analyzer() -> KnowledgeGapAnalyzer:
    return gap_analyzer


def get_rec_engine() -> LearningRecommendationEngine:
    return rec_engine


def get_path_generator() -> LearningPathGenerator:
    return path_generator


def get_skill_repo() -> SkillRepository:
    return skill_repo
