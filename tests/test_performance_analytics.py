"""Tests for Developer Performance Analytics (Phase 19)."""

from datetime import UTC, datetime

from prism.intelligence.developer_intelligence_engine import (
    DeveloperIntelligenceEngine,
)
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.developer_intelligence_models import (
    DeveloperPerformanceSnapshot,
)
from prism.intelligence.models.skill_models import SkillEvidence
from prism.intelligence.performance_analytics import (
    DeveloperPerformanceAnalytics,
)
from prism.intelligence.skill_graph import SkillGraphBuilder
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryIntelligenceRepository,
    InMemoryLearningRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
)


def _setup_analytics() -> tuple[
    DeveloperPerformanceAnalytics,
    InMemoryIntelligenceRepository,
    SkillTracker,
    InMemoryActivityRepository,
]:
    intel_repo = InMemoryIntelligenceRepository()
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    skill_repo = InMemorySkillRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    learning_repo = InMemoryLearningRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    graph = SkillGraphBuilder.build_default_graph(repository=graph_repo)
    gap_analyzer = KnowledgeGapAnalyzer(skill_graph=graph)

    dev_repo.create_developer("dev_analyst", name="Analyst", email="analyst@prism.dev")
    skill_tracker = SkillTracker(repository=skill_repo, developer_repo=dev_repo)
    intel_engine = DeveloperIntelligenceEngine(
        intelligence_repo=intel_repo,
        skill_tracker=skill_tracker,
        activity_repo=act_repo,
        gap_analyzer=gap_analyzer,
    )

    analytics = DeveloperPerformanceAnalytics(
        intelligence_engine=intel_engine,
        skill_tracker=skill_tracker,
        skill_graph=graph,
        intelligence_repo=intel_repo,
        learning_repo=learning_repo,
        activity_repo=act_repo,
    )
    return analytics, intel_repo, skill_tracker, act_repo


def test_performance_analytics_overview():
    analytics, _intel_repo, skill_tracker, act_repo = _setup_analytics()
    now = datetime.now(UTC)

    # Ingest evidence
    for sk in ["Python", "Docker"]:
        skill_tracker.record_evidence(
            SkillEvidence(
                evidence_id=f"ev_{sk}",
                developer_id="dev_analyst",
                skill_name=sk,
                skill_id=sk.lower(),
                evidence_type="commit",
                description=f"Built with {sk}",
                evidence_source="git",
                evidence_strength=1.5,
                confidence_score=0.95,
                complexity_score=0.7,
                timestamp=now,
            )
        )

    act_repo.save(
        DeveloperActivity(
            event_id="act_1",
            developer_id="dev_analyst",
            event_type="test_run",
            timestamp=now,
            project_path="/proj",
            metadata={"status": "passed"},
        )
    )

    overview = analytics.get_overview("dev_analyst")
    assert overview.developer_id == "dev_analyst"
    assert overview.total_activities >= 1
    assert overview.verified_skills_count >= 2
    assert len(overview.role_readiness) > 0

    backend_role = next(
        (
            r
            for r in overview.role_readiness
            if r.role_name.lower().replace(" ", "_") == "backend_developer"
        ),
        None,
    )
    assert backend_role is not None
    assert (
        "Python" in backend_role.missing_skills
        or "Python" in backend_role.mastered_skills
    )


def test_skill_improvement_analytics():
    analytics, _intel_repo, skill_tracker, _act_repo = _setup_analytics()
    now = datetime.now(UTC)

    skill_tracker.record_evidence(
        SkillEvidence(
            evidence_id="ev_sql",
            developer_id="dev_analyst",
            skill_name="SQLAlchemy",
            skill_id="sqlalchemy",
            evidence_type="review",
            description="Reviewed migrations",
            evidence_source="git",
            evidence_strength=1.4,
            confidence_score=0.9,
            complexity_score=0.6,
            timestamp=now,
        )
    )

    improvement = analytics.get_skill_improvement("dev_analyst")
    assert improvement.developer_id == "dev_analyst"
    assert isinstance(improvement.improving_skills, list)
    assert isinstance(improvement.trends, list)


def test_learning_progress_analytics():
    analytics, _intel_repo, _skill_tracker, _act_repo = _setup_analytics()
    progress = analytics.get_learning_progress("dev_analyst")
    assert progress.developer_id == "dev_analyst"
    assert progress.total_goals_tracked >= 0


def test_historical_snapshots():
    analytics, intel_repo, _skill_tracker, _act_repo = _setup_analytics()
    now = datetime.now(UTC)

    snap = DeveloperPerformanceSnapshot(
        snapshot_id="snap_1",
        developer_id="dev_analyst",
        timestamp=now,
        total_activities=5,
        verified_skills_count=3,
        average_proficiency_score=75.0,
        active_knowledge_gaps_count=1,
        tasks_completed_count=2,
        task_success_rate=1.0,
        learning_consistency_score=0.85,
        role_readiness_scores={"backend_developer": 0.6},
    )
    intel_repo.save_snapshot(snap)

    history = analytics.get_historical_snapshots("dev_analyst")
    assert len(history) == 1
    assert history[0].snapshot_id == "snap_1"
    assert history[0].task_success_rate == 1.0


def test_performance_analytics_empty_developer_id():
    analytics, _, _, _ = _setup_analytics()
    try:
        analytics.get_overview(" ")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "Developer ID cannot be empty" in str(e)


def test_historical_snapshots_fallback_without_repo():
    analytics, _intel_repo, _skill_tracker, _ = _setup_analytics()
    analytics.intelligence_repo = None  # Force fallback path

    history = analytics.get_historical_snapshots("dev_analyst")
    assert isinstance(history, list)
    assert len(history) >= 1
    assert history[0].developer_id == "dev_analyst"


def test_role_readiness_with_mastered_skill():
    analytics, _intel_repo, skill_tracker, _ = _setup_analytics()
    now = datetime.now(UTC)

    # Record sufficient evidence to make Python intermediate/mastered
    for i in range(6):
        skill_tracker.record_evidence(
            SkillEvidence(
                evidence_id=f"ev_py_mastered_{i}",
                developer_id="dev_analyst",
                skill_name="Python",
                skill_id="python",
                evidence_type="test_pass" if i == 0 else "commit",
                description=f"Advanced commit {i}",
                evidence_source="git",
                evidence_strength=2.0,
                confidence_score=0.95,
                complexity_score=0.8,
                timestamp=now,
                project_path="/proj_a" if i % 2 == 0 else "/proj_b",
            )
        )

    overview = analytics.get_overview("dev_analyst")
    backend = next(
        (r for r in overview.role_readiness if "backend" in r.role_name.lower()),
        None,
    )
    assert backend is not None
    assert "Python" in backend.mastered_skills
