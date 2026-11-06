from prism.config.settings import settings
from prism.evaluation.engine import TaskEvaluationEngine
from prism.intelligence.activity_intelligence_service import (
    DeveloperActivityIntelligenceService,
)
from prism.intelligence.developer_activity import ActivityRecorder
from prism.intelligence.developer_behavior_analyzer import (
    DeveloperBehaviorAnalyzer,
)
from prism.intelligence.developer_identity import DeveloperIdentityService
from prism.intelligence.developer_intelligence_engine import (
    DeveloperIntelligenceEngine,
)
from prism.intelligence.developer_session import DeveloperSessionService
from prism.intelligence.intelligence_orchestrator import (
    CrossModuleIntelligenceOrchestrator,
)
from prism.intelligence.intelligent_feedback_engine import (
    IntelligentFeedbackEngine,
)
from prism.intelligence.performance_analytics import (
    DeveloperPerformanceAnalytics,
)
from prism.intelligence.skill_evidence_engine import SkillEvidenceEngine
from prism.intelligence.skill_graph import SkillGraph, SkillGraphBuilder
from prism.intelligence.skill_tracker import SkillTracker
from prism.intelligence.task_recommendation_engine import (
    TaskRecommendationEngine,
)
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.learning_adaptation_engine import LearningAdaptationEngine
from prism.learning.learning_path_generator import LearningPathGenerator
from prism.learning.progress_tracker import LearningProgressTracker
from prism.learning.recommendation_engine import LearningRecommendationEngine
from prism.llm.context_builder import LLMContextBuilder
from prism.llm.service import LLMService
from prism.logging.logger import get_logger
from prism.mcp.service import MCPService
from prism.mentoring.adaptive_engine import AdaptiveMentoringEngine
from prism.mentoring.context_builder import MentorContextBuilder
from prism.mentoring.engine import MentoringEngine
from prism.mentoring.guided_learning_service import GuidedLearningService
from prism.mentoring.response_generator import DeterministicMentorGenerator
from prism.rag.embeddings import DeterministicEmbeddingProvider
from prism.rag.service import RAGService
from prism.rag.vector_store import VectorStore
from prism.reporting.report_generator import DeveloperReportGenerator
from prism.storage.bootstrap import check_db_connection
from prism.storage.database import get_session_factory
from prism.storage.repositories.base import (
    ActivityRepository,
    DeveloperRepository,
    DeveloperSessionRepository,
    IntelligenceRepository,
    LearningRepository,
    SkillGraphRepository,
    SkillRepository,
    TaskPlatformRepository,
)
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryIntelligenceRepository,
    InMemoryLearningRepository,
    InMemorySessionRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
    InMemoryTaskPlatformRepository,
)
from prism.storage.repositories.mysql_activity_repo import (
    MySQLActivityRepository,
)
from prism.storage.repositories.mysql_developer_repo import (
    MySQLDeveloperRepository,
)
from prism.storage.repositories.mysql_graph_repo import MySQLSkillGraphRepository
from prism.storage.repositories.mysql_intelligence_repo import (
    MySQLIntelligenceRepository,
)
from prism.storage.repositories.mysql_learning_repo import (
    MySQLLearningRepository,
)
from prism.storage.repositories.mysql_session_repo import MySQLSessionRepository
from prism.storage.repositories.mysql_skill_repo import MySQLSkillRepository
from prism.storage.repositories.mysql_task_platform_repo import (
    MySQLTaskPlatformRepository,
)

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


def init_intelligence_repository(
    backend: str | None = None,
) -> IntelligenceRepository:
    """Initialize intelligence repository based on storage backend configuration."""
    selected_backend = (backend or settings.storage_backend).strip().lower()

    if selected_backend == "memory":
        return InMemoryIntelligenceRepository()

    if selected_backend == "mysql":
        if not check_db_connection():
            error_msg = (
                f"CRITICAL: Failed to connect to MySQL database at "
                f"{settings.db_host}:{settings.db_port}/{settings.db_name} "
                "for intelligence repository."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        sf = get_session_factory()
        return MySQLIntelligenceRepository(sf)

    raise ValueError(
        f"Unsupported storage backend '{selected_backend}'. Expected 'mysql' or 'memory'."
    )


def init_task_platform_repository(
    backend: str | None = None,
    dev_repo: DeveloperRepository | None = None,
) -> TaskPlatformRepository:
    """Initialize task platform repository based on storage backend configuration."""
    selected_backend = (backend or settings.storage_backend).strip().lower()

    if selected_backend == "memory":
        return InMemoryTaskPlatformRepository(
            dev_repo=dev_repo
            if isinstance(dev_repo, InMemoryDeveloperRepository)
            else None
        )

    if selected_backend == "mysql":
        if not check_db_connection():
            error_msg = (
                f"CRITICAL: Failed to connect to MySQL database at "
                f"{settings.db_host}:{settings.db_port}/{settings.db_name} "
                "for task platform repository."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        sf = get_session_factory()
        return MySQLTaskPlatformRepository(sf, developer_repo=dev_repo)

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

intelligence_repo = init_intelligence_repository()
task_platform_repo = init_task_platform_repository(dev_repo=developer_repo)

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

# Skill graph initialization
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

# Phase 19 Developer Intelligence & Adaptive Mentoring Engines
intelligence_engine = DeveloperIntelligenceEngine(
    intelligence_repo=intelligence_repo,
    skill_tracker=skill_tracker,
    activity_repo=activity_repo,
    gap_analyzer=gap_analyzer,
)

performance_analytics = DeveloperPerformanceAnalytics(
    intelligence_engine=intelligence_engine,
    skill_tracker=skill_tracker,
    skill_graph=skill_graph,
    intelligence_repo=intelligence_repo,
    learning_repo=learning_repo,
    activity_repo=activity_repo,
)

task_engine = TaskRecommendationEngine(
    skill_tracker=skill_tracker,
    gap_analyzer=gap_analyzer,
    skill_graph=skill_graph,
    intelligence_repo=intelligence_repo,
)

feedback_engine = IntelligentFeedbackEngine(
    intelligence_repo=intelligence_repo,
    intelligence_engine=intelligence_engine,
)

adaptation_engine = LearningAdaptationEngine(
    intelligence_repo=intelligence_repo,
    intelligence_engine=intelligence_engine,
    gap_analyzer=gap_analyzer,
)

# Phase 20 LLM and RAG Services
llm_service = LLMService()
llm_context_builder = LLMContextBuilder(
    intelligence_engine=intelligence_engine,
    skill_tracker=skill_tracker,
    gap_analyzer=gap_analyzer,
    task_engine=task_engine,
    intelligence_repo=intelligence_repo,
)
rag_service = RAGService(
    embedding_provider=DeterministicEmbeddingProvider(),
    vector_store=VectorStore(storage_path=settings.rag_storage_path),
)

adaptive_mentoring_engine = AdaptiveMentoringEngine(
    intelligence_repo=intelligence_repo,
    base_mentor_engine=mentoring_engine,
    intelligence_engine=intelligence_engine,
    task_engine=task_engine,
    llm_service=llm_service,
    context_builder=llm_context_builder,
    rag_service=rag_service,
)

intelligence_orchestrator = CrossModuleIntelligenceOrchestrator(
    intelligence_repo=intelligence_repo,
    intelligence_engine=intelligence_engine,
    performance_analytics=performance_analytics,
    task_engine=task_engine,
    feedback_engine=feedback_engine,
    adaptation_engine=adaptation_engine,
    adaptive_mentor=adaptive_mentoring_engine,
    skill_evidence_engine=skill_evidence_engine,
    skill_tracker=skill_tracker,
    gap_analyzer=gap_analyzer,
    session_service=session_service,
)

# AI-Powered Developer Platform Engines (Task, Evaluation, Guided Learning, Reports, MCP)
guided_learning_service = GuidedLearningService(
    task_platform_repo=task_platform_repo,
    task_engine=task_engine,
    skill_tracker=skill_tracker,
    gap_analyzer=gap_analyzer,
    llm_service=llm_service,
    rag_service=rag_service,
)

evaluation_engine = TaskEvaluationEngine(
    task_platform_repo=task_platform_repo,
    task_engine=task_engine,
    skill_tracker=skill_tracker,
    llm_service=llm_service,
)

report_generator = DeveloperReportGenerator(
    task_platform_repo=task_platform_repo,
    intelligence_repo=intelligence_repo,
    skill_tracker=skill_tracker,
    developer_repo=developer_repo,
    activity_repo=activity_repo,
)

mcp_service = MCPService(
    task_platform_repo=task_platform_repo,
    task_engine=task_engine,
    evaluation_engine=evaluation_engine,
    report_generator=report_generator,
    rag_service=rag_service,
)


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


def get_intelligence_repo() -> IntelligenceRepository:
    return intelligence_repo


def get_intelligence_engine() -> DeveloperIntelligenceEngine:
    return intelligence_engine


def get_performance_analytics() -> DeveloperPerformanceAnalytics:
    return performance_analytics


def get_task_engine() -> TaskRecommendationEngine:
    return task_engine


def get_feedback_engine() -> IntelligentFeedbackEngine:
    return feedback_engine


def get_adaptation_engine() -> LearningAdaptationEngine:
    return adaptation_engine


def get_adaptive_mentoring_engine() -> AdaptiveMentoringEngine:
    return adaptive_mentoring_engine


def get_intelligence_orchestrator() -> CrossModuleIntelligenceOrchestrator:
    return intelligence_orchestrator


def get_llm_service() -> LLMService:
    return llm_service


def get_llm_context_builder() -> LLMContextBuilder:
    return llm_context_builder


def get_rag_service() -> RAGService:
    return rag_service


def get_task_platform_repo() -> TaskPlatformRepository:
    return task_platform_repo


def get_guided_learning_service() -> GuidedLearningService:
    return guided_learning_service


def get_evaluation_engine() -> TaskEvaluationEngine:
    return evaluation_engine


def get_report_generator() -> DeveloperReportGenerator:
    return report_generator


def get_mcp_service() -> MCPService:
    return mcp_service
