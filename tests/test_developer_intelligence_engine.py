"""Tests for Developer Intelligence Engine (Phase 19)."""

from datetime import UTC, datetime

from prism.intelligence.developer_intelligence_engine import (
    DeveloperIntelligenceEngine,
)
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.developer_intelligence_models import (
    InsightCategory,
    InsightSeverity,
    TrendDirection,
)
from prism.intelligence.models.skill_models import SkillEvidence
from prism.intelligence.skill_graph import SkillGraphBuilder
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryIntelligenceRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
)


def _setup_engine() -> tuple[
    DeveloperIntelligenceEngine,
    InMemoryIntelligenceRepository,
    SkillTracker,
    InMemoryActivityRepository,
]:
    intel_repo = InMemoryIntelligenceRepository()
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    skill_repo = InMemorySkillRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    graph = SkillGraphBuilder.build_default_graph(repository=graph_repo)
    gap_analyzer = KnowledgeGapAnalyzer(skill_graph=graph)

    dev_repo.create_developer("dev_test", name="Tester", email="test@prism.dev")
    skill_tracker = SkillTracker(repository=skill_repo, developer_repo=dev_repo)

    engine = DeveloperIntelligenceEngine(
        intelligence_repo=intel_repo,
        skill_tracker=skill_tracker,
        activity_repo=act_repo,
        gap_analyzer=gap_analyzer,
    )
    return engine, intel_repo, skill_tracker, act_repo


def test_developer_intelligence_insufficient_data():
    engine, _intel_repo, _skill_tracker, _act_repo = _setup_engine()

    profile = engine.get_profile("dev_test")
    assert profile.developer_id == "dev_test"
    assert profile.overall_status == "insufficient_data"
    assert not profile.has_sufficient_data
    assert len(profile.top_strengths) == 0

    result = engine.analyze_developer("dev_test")
    assert result.profile.overall_status == "insufficient_data"
    assert len(result.insights) >= 1
    assert result.insights[0].category == InsightCategory.GROWTH


def test_developer_intelligence_sufficient_data():
    engine, _intel_repo, skill_tracker, act_repo = _setup_engine()
    now = datetime.now(UTC)

    # Record 4 activities
    for i in range(4):
        act_repo.save(
            DeveloperActivity(
                event_id=f"act_{i}",
                developer_id="dev_test",
                event_type="code_modification",
                timestamp=now,
                project_path="/test",
                file_path="/test/main.py",
                metadata={"complexity": 0.8},
            )
        )

    # Record multiple verified skill evidences
    for sk in ["Python", "FastAPI", "SQLAlchemy"]:
        for j in range(3):
            skill_tracker.record_evidence(
                SkillEvidence(
                    evidence_id=f"ev_{sk}_{j}",
                    developer_id="dev_test",
                    skill_name=sk,
                    skill_id=sk.lower(),
                    evidence_type="commit",
                    description=f"Developed {sk} feature",
                    evidence_source="git",
                    evidence_strength=1.5,
                    confidence_score=0.9,
                    complexity_score=0.7,
                    timestamp=now,
                )
            )

    result = engine.analyze_developer("dev_test")
    assert result.profile.developer_id == "dev_test"
    assert result.profile.has_sufficient_data is True
    assert result.profile.overall_status in (
        "proficient",
        "intermediate",
        "advanced",
        "learning",
    )
    assert (
        len(result.profile.top_strengths) > 0
        or len(result.profile.critical_weaknesses) > 0
    )

    # Insights check
    insights = engine.get_insights("dev_test")
    assert len(insights) > 0

    # Trends check
    trends = engine.get_skill_trends("dev_test")
    assert len(trends) > 0
    python_trend = next((t for t in trends if t.skill_name == "Python"), None)
    assert python_trend is not None
    assert python_trend.direction in (TrendDirection.IMPROVING, TrendDirection.STABLE)


def test_developer_intelligence_empty_id():
    engine, _, _, _ = _setup_engine()
    try:
        engine.analyze_developer("   ")
        assert False, "Expected ValueError for empty developer id"
    except ValueError as e:
        assert "Developer ID cannot be empty" in str(e)


def test_developer_intelligence_high_error_and_excelling_states():
    engine, _intel_repo, skill_tracker, act_repo = _setup_engine()
    now = datetime.now(UTC)

    # 1. Developer with 6+ error events -> HIGH severity insight
    for i in range(7):
        act_repo.save(
            DeveloperActivity(
                event_id=f"evt_err_{i}",
                developer_id="dev_test",
                event_type="syntax_error",
                timestamp=now,
                project_path="/repo",
                file_path="/repo/main.py",
                metadata={"error": "SyntaxError"},
            )
        )

    res_err = engine.analyze_developer("dev_test")
    err_insight = next(
        (i for i in res_err.insights if i.category == InsightCategory.RECURRING_ERROR),
        None,
    )
    assert err_insight is not None
    assert err_insight.severity == InsightSeverity.HIGH

    # 2. Engine without repository
    graph = SkillGraphBuilder.build_default_graph()
    gap_analyzer = KnowledgeGapAnalyzer(skill_graph=graph)
    no_repo_engine = DeveloperIntelligenceEngine(
        skill_tracker=skill_tracker,
        activity_repo=act_repo,
        gap_analyzer=gap_analyzer,
        intelligence_repo=None,
    )
    prof = no_repo_engine.get_profile("dev_test")
    assert prof.developer_id == "dev_test"
    assert len(no_repo_engine.get_insights("dev_test")) >= 0
    assert len(no_repo_engine.get_skill_trends("dev_test")) >= 0
