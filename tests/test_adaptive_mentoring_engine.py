"""Tests for Adaptive Mentoring Engine (Phase 19)."""

from datetime import UTC, datetime

from prism.intelligence.developer_intelligence_engine import (
    DeveloperIntelligenceEngine,
)
from prism.intelligence.models.developer_intelligence_models import (
    DeveloperIntelligenceProfile,
    SkillTrend,
    TrendDirection,
)
from prism.intelligence.skill_graph import SkillGraphBuilder
from prism.intelligence.skill_tracker import SkillTracker
from prism.intelligence.task_recommendation_engine import (
    TaskRecommendationEngine,
)
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.mentoring.adaptive_engine import AdaptiveMentoringEngine
from prism.mentoring.engine import MentoringEngine
from prism.mentoring.models import (
    AdaptiveMentorRequest,
    MentoringSessionRecord,
    MentoringStrategy,
)
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryIntelligenceRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
)


def _setup_adaptive_mentor() -> tuple[
    AdaptiveMentoringEngine,
    InMemoryIntelligenceRepository,
    DeveloperIntelligenceEngine,
    TaskRecommendationEngine,
]:
    intel_repo = InMemoryIntelligenceRepository()
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    skill_repo = InMemorySkillRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    graph = SkillGraphBuilder.build_default_graph(repository=graph_repo)
    gap_analyzer = KnowledgeGapAnalyzer(skill_graph=graph)

    dev_repo.create_developer("dev_mentee", name="Mentee", email="mentee@prism.dev")
    skill_tracker = SkillTracker(repository=skill_repo, developer_repo=dev_repo)
    intel_engine = DeveloperIntelligenceEngine(
        intelligence_repo=intel_repo,
        skill_tracker=skill_tracker,
        activity_repo=act_repo,
        gap_analyzer=gap_analyzer,
    )

    task_engine = TaskRecommendationEngine(
        skill_tracker=skill_tracker,
        gap_analyzer=gap_analyzer,
        skill_graph=graph,
        intelligence_repo=intel_repo,
    )

    mentor_engine = AdaptiveMentoringEngine(
        intelligence_repo=intel_repo,
        base_mentor_engine=MentoringEngine(),
        intelligence_engine=intel_engine,
        task_engine=task_engine,
    )
    return mentor_engine, intel_repo, intel_engine, task_engine


def test_adaptive_mentoring_debugging_strategy():
    mentor_engine, _intel_repo, _intel_engine, _task_engine = _setup_adaptive_mentor()

    req = AdaptiveMentorRequest(
        developer_id="dev_mentee",
        query="I have a broken database connection error and need to fix the traceback",
    )
    res = mentor_engine.request_adaptive_mentoring(req)
    assert res.developer_id == "dev_mentee"
    assert res.selected_strategy == MentoringStrategy.DEBUGGING_GUIDANCE
    assert res.explanation_complexity == "targeted"
    assert len(res.actionable_steps) > 0

    sessions = mentor_engine.get_session_history("dev_mentee")
    assert len(sessions) == 1
    assert sessions[0].strategy == MentoringStrategy.DEBUGGING_GUIDANCE


def test_adaptive_mentoring_practical_exercise_and_advanced_guidance():
    mentor_engine, _intel_repo, _intel_engine, _task_engine = _setup_adaptive_mentor()

    # Practice query
    req1 = AdaptiveMentorRequest(
        developer_id="dev_mentee",
        query="Give me a hands-on exercise project to practice FastAPI endpoints",
    )
    res1 = mentor_engine.request_adaptive_mentoring(req1)
    assert res1.selected_strategy == MentoringStrategy.PRACTICAL_EXERCISE
    assert "Applied Hands-on Practice" in res1.explanation

    # Advanced architecture query
    req2 = AdaptiveMentorRequest(
        developer_id="dev_mentee",
        query="How to optimize concurrency architecture for scale?",
    )
    res2 = mentor_engine.request_adaptive_mentoring(req2)
    assert res2.selected_strategy == MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE
    assert res2.explanation_complexity == "advanced"
    assert res2.mentoring_difficulty == "advanced"


def test_adaptive_mentoring_with_profile_trends_and_tasks():
    mentor_engine, _intel_repo, intel_engine, _task_engine = _setup_adaptive_mentor()

    # Mock profile with trends
    mock_profile = DeveloperIntelligenceProfile(
        developer_id="dev_mentee",
        overall_status="learning",
        top_strengths=["Docker"],
        critical_weaknesses=["Python"],
        active_gaps=["Python"],
        trends={
            "Python": SkillTrend(
                skill_name="Python",
                direction=TrendDirection.IMPROVING,
                previous_level="novice",
                current_level="novice",
                evidence_growth_rate=0.5,
                change_description="Growing",
                confidence=0.9,
            ),
            "Docker": SkillTrend(
                skill_name="Docker",
                direction=TrendDirection.IMPROVING,
                previous_level="proficient",
                current_level="proficient",
                evidence_growth_rate=0.8,
                change_description="Solid",
                confidence=0.95,
            ),
        },
        has_sufficient_data=True,
    )
    intel_engine.get_profile = lambda dev_id: mock_profile  # type: ignore[method-assign]

    # Target novice skill -> CONCEPTUAL_EXPLANATION
    res_novice = mentor_engine.request_adaptive_mentoring(
        AdaptiveMentorRequest(
            developer_id="dev_mentee",
            query="Explain Python generators",
            target_skill="Python",
            context_metadata={"target_role": "backend_developer"},
        )
    )
    assert res_novice.selected_strategy == MentoringStrategy.CONCEPTUAL_EXPLANATION
    assert res_novice.mentoring_difficulty == "beginner"
    assert "Python" in res_novice.targeted_knowledge_gaps

    # Target proficient skill -> ADVANCED_TECHNICAL_GUIDANCE
    res_prof = mentor_engine.request_adaptive_mentoring(
        AdaptiveMentorRequest(
            developer_id="dev_mentee",
            query="Optimizing Docker layers",
            target_skill="Docker",
        )
    )
    assert res_prof.selected_strategy == MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE
    assert res_prof.mentoring_difficulty == "advanced"


def test_adaptive_mentoring_preferred_strategy_override():
    mentor_engine, _intel_repo, _intel_engine, _task_engine = _setup_adaptive_mentor()

    req = AdaptiveMentorRequest(
        developer_id="dev_mentee",
        query="Tell me about Python decorators",
        preferred_strategy=MentoringStrategy.CONCEPTUAL_EXPLANATION,
    )
    res = mentor_engine.request_adaptive_mentoring(req)
    assert res.selected_strategy == MentoringStrategy.CONCEPTUAL_EXPLANATION
    assert res.explanation_complexity == "foundational"
    assert "Foundational Core Concepts" in res.explanation


def test_adaptive_mentoring_effectiveness():
    mentor_engine, intel_repo, intel_engine, _task_engine = _setup_adaptive_mentor()
    now = datetime.now(UTC)

    # Mock profile with improving trends
    mock_profile = DeveloperIntelligenceProfile(
        developer_id="dev_mentee",
        trends={
            "Python": SkillTrend(
                skill_name="Python",
                direction=TrendDirection.IMPROVING,
                previous_level="novice",
                current_level="intermediate",
                change_description="Improved",
                confidence=1.0,
            )
        },
    )
    intel_engine.get_profile = lambda dev_id: mock_profile  # type: ignore[method-assign]

    eff0 = mentor_engine.get_mentoring_effectiveness("dev_mentee")
    assert eff0.total_sessions == 0
    assert eff0.effectiveness_score == 0.0

    intel_repo.save_mentoring_session(
        MentoringSessionRecord(
            session_id="ms_01",
            developer_id="dev_mentee",
            strategy=MentoringStrategy.GUIDED_IMPLEMENTATION,
            query="API design",
            summary="Guided walkthrough",
            outcome_rating=4.5,
            created_at=now,
        )
    )

    eff1 = mentor_engine.get_mentoring_effectiveness("dev_mentee")
    assert eff1.total_sessions == 1
    assert eff1.average_rating == 4.5
    assert eff1.effectiveness_score > 0.6
    assert eff1.skill_improvements_correlated == 1
    assert "guided_implementation" in eff1.strategy_distribution


def test_adaptive_mentoring_validation():
    mentor_engine, _intel_repo, _intel_engine, _ = _setup_adaptive_mentor()
    try:
        mentor_engine.request_adaptive_mentoring(
            AdaptiveMentorRequest(developer_id="", query="Hello")
        )
        assert False, "Expected ValueError for empty developer_id"
    except ValueError as e:
        assert "Developer ID cannot be empty" in str(e)

    try:
        mentor_engine.request_adaptive_mentoring(
            AdaptiveMentorRequest(developer_id="dev_mentee", query="   ")
        )
        assert False, "Expected ValueError for empty query"
    except ValueError as e:
        assert "Query cannot be empty" in str(e)


def test_adaptive_mentoring_strategy_selection_from_gaps_and_trends():
    mentor_engine, _intel_repo, intel_engine, _ = _setup_adaptive_mentor()

    # 1. Active gap triggers STEP_BY_STEP_LEARNING
    gap_profile = DeveloperIntelligenceProfile(
        developer_id="dev_mentee",
        active_gaps=["Docker"],
    )
    intel_engine.get_profile = lambda dev_id: gap_profile  # type: ignore[method-assign]

    res = mentor_engine.request_adaptive_mentoring(
        AdaptiveMentorRequest(
            developer_id="dev_mentee",
            query="Tell me about container workflows",
            target_skill="Docker",
        )
    )
    assert res.selected_strategy == MentoringStrategy.STEP_BY_STEP_LEARNING
    assert res.explanation_complexity == "foundational"

    # 2. Proficient trend triggers ADVANCED_TECHNICAL_GUIDANCE
    adv_profile = DeveloperIntelligenceProfile(
        developer_id="dev_mentee",
        trends={
            "Python": SkillTrend(
                skill_name="Python",
                direction=TrendDirection.STABLE,
                previous_level="proficient",
                current_level="proficient",
                change_description="Solid",
                confidence=0.9,
            )
        },
    )
    intel_engine.get_profile = lambda dev_id: adv_profile  # type: ignore[method-assign]

    res_adv = mentor_engine.request_adaptive_mentoring(
        AdaptiveMentorRequest(
            developer_id="dev_mentee",
            query="Deep dive into generators",
            target_skill="Python",
        )
    )
    assert res_adv.selected_strategy == MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE
    assert res_adv.explanation_complexity == "advanced"


def test_adaptive_mentoring_resilience_to_failures():
    mentor_engine, intel_repo, intel_engine, _ = _setup_adaptive_mentor()

    # get_profile failure during request
    def _fail_get_profile(dev_id: str):
        raise RuntimeError("Engine offline")

    intel_engine.get_profile = _fail_get_profile  # type: ignore[method-assign]

    res = mentor_engine.request_adaptive_mentoring(
        AdaptiveMentorRequest(
            developer_id="dev_mentee",
            query="Explain recursion simply",
        )
    )
    assert res.developer_id == "dev_mentee"

    # save_mentoring_session failure during request
    def _fail_save_session(rec):
        raise OSError("Disk write failed")

    intel_repo.save_mentoring_session = _fail_save_session  # type: ignore[method-assign]
    res2 = mentor_engine.request_adaptive_mentoring(
        AdaptiveMentorRequest(
            developer_id="dev_mentee",
            query="Explain pointers",
        )
    )
    assert res2.developer_id == "dev_mentee"

    # get_profile failure during get_mentoring_effectiveness
    eff = mentor_engine.get_mentoring_effectiveness("dev_mentee")
    assert eff.developer_id == "dev_mentee"
