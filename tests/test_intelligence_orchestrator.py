"""Tests for Cross-Module Intelligence Orchestrator (Phase 19)."""

from datetime import UTC, datetime

from prism.intelligence.developer_intelligence_engine import (
    DeveloperIntelligenceEngine,
)
from prism.intelligence.intelligence_orchestrator import (
    CrossModuleIntelligenceOrchestrator,
)
from prism.intelligence.intelligent_feedback_engine import (
    IntelligentFeedbackEngine,
)
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.performance_analytics import (
    DeveloperPerformanceAnalytics,
)
from prism.intelligence.skill_evidence_engine import SkillEvidenceEngine
from prism.intelligence.skill_graph import SkillGraphBuilder
from prism.intelligence.skill_tracker import SkillTracker
from prism.intelligence.task_recommendation_engine import (
    TaskRecommendationEngine,
)
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.learning_adaptation_engine import LearningAdaptationEngine
from prism.mentoring.adaptive_engine import AdaptiveMentoringEngine
from prism.mentoring.engine import MentoringEngine
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryIntelligenceRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
)


def _setup_orchestrator() -> tuple[
    CrossModuleIntelligenceOrchestrator,
    InMemoryIntelligenceRepository,
    SkillTracker,
]:
    intel_repo = InMemoryIntelligenceRepository()
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    skill_repo = InMemorySkillRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    graph = SkillGraphBuilder.build_default_graph(repository=graph_repo)
    gap_analyzer = KnowledgeGapAnalyzer(skill_graph=graph)

    dev_repo.create_developer(
        "dev_orch", name="Orchestrator User", email="orch@prism.dev"
    )
    skill_tracker = SkillTracker(repository=skill_repo, developer_repo=dev_repo)
    skill_evidence_engine = SkillEvidenceEngine(skill_tracker=skill_tracker)

    intel_engine = DeveloperIntelligenceEngine(
        intelligence_repo=intel_repo,
        skill_tracker=skill_tracker,
        activity_repo=act_repo,
        gap_analyzer=gap_analyzer,
    )

    performance_analytics = DeveloperPerformanceAnalytics(
        intelligence_engine=intel_engine,
        skill_tracker=skill_tracker,
        skill_graph=graph,
        intelligence_repo=intel_repo,
        activity_repo=act_repo,
    )

    task_engine = TaskRecommendationEngine(
        skill_tracker=skill_tracker,
        gap_analyzer=gap_analyzer,
        skill_graph=graph,
        intelligence_repo=intel_repo,
    )

    feedback_engine = IntelligentFeedbackEngine(
        intelligence_repo=intel_repo,
        intelligence_engine=intel_engine,
    )

    adaptation_engine = LearningAdaptationEngine(
        intelligence_repo=intel_repo,
        intelligence_engine=intel_engine,
        gap_analyzer=gap_analyzer,
    )

    adaptive_mentor = AdaptiveMentoringEngine(
        intelligence_repo=intel_repo,
        base_mentor_engine=MentoringEngine(),
        intelligence_engine=intel_engine,
        task_engine=task_engine,
    )

    orchestrator = CrossModuleIntelligenceOrchestrator(
        intelligence_repo=intel_repo,
        intelligence_engine=intel_engine,
        performance_analytics=performance_analytics,
        task_engine=task_engine,
        feedback_engine=feedback_engine,
        adaptation_engine=adaptation_engine,
        adaptive_mentor=adaptive_mentor,
        skill_evidence_engine=skill_evidence_engine,
        skill_tracker=skill_tracker,
        gap_analyzer=gap_analyzer,
    )
    return orchestrator, intel_repo, skill_tracker


def test_orchestrate_activity_recalibration():
    orchestrator, _intel_repo, _skill_tracker = _setup_orchestrator()
    now = datetime.now(UTC)

    activity = DeveloperActivity(
        event_id="act_orch_01",
        developer_id="dev_orch",
        event_type="git_commit",
        timestamp=now,
        project_path="/projects/prism",
        file_path="/projects/prism/service.py",
        metadata={
            "language": "python",
            "skills": ["Python", "FastAPI"],
            "lines_added": 45,
        },
    )

    result = orchestrator.process_activity_and_recalibrate(
        activity, auto_generate_tasks=True
    )
    assert result["status"] == "success"
    assert result["developer_id"] == "dev_orch"
    assert result["activity_id"] == "act_orch_01"
    assert "current_learning_strategy" in result
    assert result["proactive_feedbacks_count"] >= 1


def test_run_full_developer_sync():
    orchestrator, _intel_repo, _skill_tracker = _setup_orchestrator()

    sync_result = orchestrator.run_full_developer_sync(
        developer_id="dev_orch",
        target_role="backend_developer",
    )

    assert sync_result["status"] == "synced"
    assert sync_result["developer_id"] == "dev_orch"
    assert "verified_skills_count" in sync_result
    assert "current_learning_strategy" in sync_result
    assert sync_result["recommended_tasks_count"] >= 0
