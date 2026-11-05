"""Tests for Personalized Task Recommendation Engine (Phase 19)."""

from datetime import UTC, datetime

import pytest

from prism.intelligence.models.developer_intelligence_models import (
    TaskDifficulty,
    TaskStatus,
)
from prism.intelligence.models.skill_models import SkillEvidence
from prism.intelligence.skill_graph import SkillGraphBuilder
from prism.intelligence.skill_tracker import SkillTracker
from prism.intelligence.task_recommendation_engine import (
    TaskRecommendationEngine,
)
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryIntelligenceRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
)


def _setup_task_engine() -> tuple[
    TaskRecommendationEngine,
    InMemoryIntelligenceRepository,
    SkillTracker,
]:
    intel_repo = InMemoryIntelligenceRepository()
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    skill_repo = InMemorySkillRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    _act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    graph = SkillGraphBuilder.build_default_graph(repository=graph_repo)
    gap_analyzer = KnowledgeGapAnalyzer(skill_graph=graph)

    dev_repo.create_developer("dev_tasker", name="Tasker", email="tasker@prism.dev")
    skill_tracker = SkillTracker(repository=skill_repo, developer_repo=dev_repo)

    task_engine = TaskRecommendationEngine(
        skill_tracker=skill_tracker,
        gap_analyzer=gap_analyzer,
        skill_graph=graph,
        intelligence_repo=intel_repo,
    )
    return task_engine, intel_repo, skill_tracker


def test_task_generation_and_recommendation():
    task_engine, _intel_repo, skill_tracker = _setup_task_engine()
    now = datetime.now(UTC)

    # Ingest evidence for Python so a gap like FastAPI or Docker can be targeted
    skill_tracker.record_evidence(
        SkillEvidence(
            evidence_id="ev_py_01",
            developer_id="dev_tasker",
            skill_name="Python",
            skill_id="python",
            evidence_type="commit",
            description="Python coding",
            evidence_source="git",
            evidence_strength=1.5,
            confidence_score=0.9,
            complexity_score=0.7,
            timestamp=now,
        )
    )

    recs = task_engine.generate_tasks(
        developer_id="dev_tasker",
        target_role="backend_developer",
        limit=3,
    )

    assert len(recs) > 0
    first_rec = recs[0]
    assert first_rec.task.developer_id == "dev_tasker"
    assert first_rec.task.status == TaskStatus.GENERATED
    assert first_rec.importance_score >= 1.0
    assert first_rec.task.difficulty in (
        TaskDifficulty.BEGINNER,
        TaskDifficulty.INTERMEDIATE,
        TaskDifficulty.ADVANCED,
    )

    # Verify task persisted
    saved_task = task_engine.get_task(first_rec.task.task_id)
    assert saved_task is not None
    assert saved_task.task_id == first_rec.task.task_id


def test_task_lifecycle_and_evaluation_generates_evidence():
    task_engine, intel_repo, skill_tracker = _setup_task_engine()

    recs = task_engine.generate_tasks(
        developer_id="dev_tasker",
        target_role="backend_developer",
        limit=1,
    )
    assert len(recs) == 1
    task_id = recs[0].task.task_id

    # Update status to in_progress
    updated = task_engine.update_task_status(
        task_id, "in_progress", notes="Working on API endpoints"
    )
    assert updated.status == TaskStatus.IN_PROGRESS

    # Evaluate task with success
    evaluation = task_engine.evaluate_task_completion(
        task_id=task_id,
        success=True,
        execution_notes="All integration tests passed and endpoints verified",
        artifacts=["tests/test_api.py"],
    )

    assert evaluation.passed is True
    assert evaluation.score >= 80.0
    assert evaluation.generated_evidence_id is not None
    assert len(evaluation.strengths_demonstrated) > 0

    # Verify verifiable skill evidence was automatically registered with skill tracker
    profile = skill_tracker.get_profile("dev_tasker")
    target_skill = recs[0].task.target_skill
    dev_skill = profile.get_skill(target_skill)
    assert dev_skill is not None
    assert dev_skill.evidence_count >= 1

    # Verify task outcome was recorded
    outcomes = intel_repo.get_task_outcomes("dev_tasker")
    assert len(outcomes) == 1
    assert outcomes[0].success is True


def test_task_evaluation_failure():
    task_engine, _intel_repo, _skill_tracker = _setup_task_engine()

    recs = task_engine.generate_tasks(
        developer_id="dev_tasker",
        target_role="backend_developer",
        limit=1,
    )
    task_id = recs[0].task.task_id

    evaluation = task_engine.evaluate_task_completion(
        task_id=task_id,
        success=False,
        execution_notes="Failed tests due to connection error",
    )
    assert evaluation.passed is False
    assert evaluation.generated_evidence_id is None
    assert len(evaluation.improvement_areas) > 0


def test_task_engine_validations_and_edge_cases():
    task_engine, _, _ = _setup_task_engine()

    # Empty developer_id validation
    with pytest.raises(ValueError, match="Developer ID cannot be empty"):
        task_engine.generate_tasks(developer_id="  ")

    # Target goal generation
    recs_goal = task_engine.generate_tasks(
        developer_id="dev_tasker",
        target_goal="FastAPI",
        limit=2,
    )
    assert isinstance(recs_goal, list)

    # Unknown task operations
    with pytest.raises(ValueError, match="not found"):
        task_engine.update_task_status("nonexistent_tsk", "completed")

    with pytest.raises(ValueError, match="not found"):
        task_engine.evaluate_task_completion(
            "nonexistent_tsk", success=True, execution_notes=""
        )

    # Engine without repository
    graph = SkillGraphBuilder.build_default_graph()
    gap_analyzer = KnowledgeGapAnalyzer(skill_graph=graph)
    no_repo_engine = TaskRecommendationEngine(
        skill_tracker=_setup_task_engine()[2],
        gap_analyzer=gap_analyzer,
        skill_graph=graph,
        intelligence_repo=None,
    )
    assert no_repo_engine.get_task("any_id") is None

    with pytest.raises(RuntimeError, match="Repository required"):
        no_repo_engine.update_task_status("any_id", "completed")

    with pytest.raises(RuntimeError, match="Repository required"):
        no_repo_engine.evaluate_task_completion(
            "any_id", success=True, execution_notes=""
        )


def test_task_generation_difficulty_levels_and_fallbacks():
    task_engine, _intel_repo, skill_tracker = _setup_task_engine()
    now = datetime.now(UTC)

    # 1. Generate tasks without role and without goal (active skills fallback)
    recs_active = task_engine.generate_tasks(
        developer_id="dev_tasker",
        limit=2,
    )
    assert isinstance(recs_active, list)

    # 2. Add evidence making Python beginner, then intermediate
    skill_tracker.record_evidence(
        SkillEvidence(
            evidence_id="ev_py_beg",
            developer_id="dev_tasker",
            skill_name="Python",
            skill_id="python",
            evidence_type="commit",
            description="Simple python script",
            evidence_source="git",
            evidence_strength=1.0,
            confidence_score=0.7,
            complexity_score=0.4,
            timestamp=now,
        )
    )

    recs = task_engine.generate_tasks(
        developer_id="dev_tasker",
        target_role="backend_developer",
        limit=5,
    )
    assert len(recs) >= 1
