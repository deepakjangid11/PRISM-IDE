"""Tests for Intelligent Feedback and Learning Adaptation Engines (Phase 19)."""

from datetime import UTC, datetime

from prism.intelligence.developer_intelligence_engine import (
    DeveloperIntelligenceEngine,
)
from prism.intelligence.intelligent_feedback_engine import (
    IntelligentFeedbackEngine,
)
from prism.intelligence.models.developer_intelligence_models import (
    DeveloperIntelligenceProfile,
    FeedbackCategory,
    LearningStrategyType,
    SkillTrend,
    TaskDifficulty,
    TaskEvaluation,
    TaskOutcome,
    TrendDirection,
)
from prism.intelligence.skill_graph import SkillGraphBuilder
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.learning_adaptation_engine import LearningAdaptationEngine
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryIntelligenceRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
)


def _setup_feedback_and_adaptation() -> tuple[
    IntelligentFeedbackEngine,
    LearningAdaptationEngine,
    InMemoryIntelligenceRepository,
    SkillTracker,
    DeveloperIntelligenceEngine,
]:
    intel_repo = InMemoryIntelligenceRepository()
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    skill_repo = InMemorySkillRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    graph = SkillGraphBuilder.build_default_graph(repository=graph_repo)
    gap_analyzer = KnowledgeGapAnalyzer(skill_graph=graph)

    dev_repo.create_developer("dev_learner", name="Learner", email="learner@prism.dev")
    skill_tracker = SkillTracker(repository=skill_repo, developer_repo=dev_repo)
    intel_engine = DeveloperIntelligenceEngine(
        intelligence_repo=intel_repo,
        skill_tracker=skill_tracker,
        activity_repo=act_repo,
        gap_analyzer=gap_analyzer,
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
    return feedback_engine, adaptation_engine, intel_repo, skill_tracker, intel_engine


def test_task_feedback_generation():
    feedback_engine, _, _intel_repo, _, _ = _setup_feedback_and_adaptation()
    now = datetime.now(UTC)

    # High score -> MILESTONE_ACHIEVED
    eval_milestone = TaskEvaluation(
        evaluation_id="eval_1",
        task_id="tsk_1",
        developer_id="dev_learner",
        passed=True,
        score=0.92,
        strengths_demonstrated=["Clean architecture", "Type hints"],
        feedback_message="Exceptional work!",
        evaluated_at=now,
    )
    fb1 = feedback_engine.generate_feedback_for_task(eval_milestone)
    assert fb1.category == FeedbackCategory.MILESTONE_ACHIEVED
    assert "Exceptional work!" in fb1.message

    # Moderate score -> POSITIVE
    eval_pos = TaskEvaluation(
        evaluation_id="eval_2",
        task_id="tsk_2",
        developer_id="dev_learner",
        passed=True,
        score=0.75,
        strengths_demonstrated=["Functional code"],
        feedback_message="Passes basic acceptance criteria.",
        evaluated_at=now,
    )
    fb2 = feedback_engine.generate_feedback_for_task(eval_pos)
    assert fb2.category == FeedbackCategory.POSITIVE

    # Failed -> IMPROVEMENT_REQUIRED
    eval_fail = TaskEvaluation(
        evaluation_id="eval_3",
        task_id="tsk_3",
        developer_id="dev_learner",
        passed=False,
        score=0.35,
        improvement_areas=["Missing exception handling"],
        feedback_message="Tests failed.",
        evaluated_at=now,
    )
    fb3 = feedback_engine.generate_feedback_for_task(eval_fail)
    assert fb3.category == FeedbackCategory.IMPROVEMENT_REQUIRED

    # Check history
    history = feedback_engine.get_feedback_history("dev_learner")
    assert len(history) == 3


def test_proactive_feedback_insufficient_data():
    feedback_engine, _, _, _, _ = _setup_feedback_and_adaptation()
    fbs = feedback_engine.generate_proactive_feedback("dev_learner")
    assert len(fbs) == 1
    assert "Welcome to PRISM" in fbs[0].message


def test_proactive_feedback_with_sufficient_data():
    feedback_engine, _, _intel_repo, _, intel_engine = _setup_feedback_and_adaptation()
    mock_profile = DeveloperIntelligenceProfile(
        developer_id="dev_learner",
        overall_status="intermediate",
        top_strengths=["Python"],
        critical_weaknesses=["SQLAlchemy"],
        active_gaps=["FastAPI"],
        has_sufficient_data=True,
    )
    intel_engine.get_profile = lambda dev_id: mock_profile  # type: ignore[method-assign]

    fbs = feedback_engine.generate_proactive_feedback("dev_learner")
    assert len(fbs) >= 2
    categories = [fb.category for fb in fbs]
    assert FeedbackCategory.KNOWLEDGE_GAP in categories
    assert FeedbackCategory.PERFORMANCE_WARNING in categories
    assert FeedbackCategory.POSITIVE in categories


def test_learning_adaptation_standard_and_remediation():
    _, adaptation_engine, intel_repo, _, _ = _setup_feedback_and_adaptation()
    now = datetime.now(UTC)

    # Initial strategy is standard
    adapt1 = adaptation_engine.adapt_strategy("dev_learner")
    assert adapt1.new_strategy == LearningStrategyType.STANDARD
    assert adapt1.adjusted_difficulty == TaskDifficulty.INTERMEDIATE

    # Simulate 3 task failures
    for i in range(3):
        intel_repo.save_task_outcome(
            TaskOutcome(
                outcome_id=f"out_f_{i}",
                task_id=f"tsk_f_{i}",
                developer_id="dev_learner",
                success=False,
                execution_notes="Failed tests",
                recorded_at=now,
            )
        )

    adapt2 = adaptation_engine.adapt_strategy("dev_learner")
    assert adapt2.new_strategy == LearningStrategyType.REMEDIATION
    assert adapt2.adjusted_difficulty == TaskDifficulty.BEGINNER
    assert "Elevated failure rate" in adapt2.adaptation_reason

    # Verify history
    history = adaptation_engine.get_adaptation_history("dev_learner")
    assert len(history) == 2
    latest = adaptation_engine.get_current_strategy("dev_learner")
    assert latest is not None
    assert latest.new_strategy == LearningStrategyType.REMEDIATION


def test_learning_adaptation_stalled_skills_practice_intensive():
    _, adaptation_engine, _intel_repo, _, intel_engine = (
        _setup_feedback_and_adaptation()
    )
    mock_profile = DeveloperIntelligenceProfile(
        developer_id="dev_learner",
        trends={
            "FastAPI": SkillTrend(
                skill_name="FastAPI",
                direction=TrendDirection.REGRESSING,
                previous_level="intermediate",
                current_level="novice",
                change_description="Stalled",
            )
        },
    )
    intel_engine.get_profile = lambda dev_id: mock_profile  # type: ignore[method-assign]

    adapt = adaptation_engine.adapt_strategy("dev_learner")
    assert adapt.new_strategy == LearningStrategyType.PRACTICE_INTENSIVE
    assert "FastAPI" in adapt.stalled_skills_detected


def test_learning_adaptation_accelerated_strategy():
    _, adaptation_engine, intel_repo, _, intel_engine = _setup_feedback_and_adaptation()
    now = datetime.now(UTC)

    # 3 successful task outcomes
    for i in range(3):
        intel_repo.save_task_outcome(
            TaskOutcome(
                outcome_id=f"out_s_{i}",
                task_id=f"tsk_s_{i}",
                developer_id="dev_learner",
                success=True,
                execution_notes="Passed",
                recorded_at=now,
            )
        )

    mock_profile = DeveloperIntelligenceProfile(
        developer_id="dev_learner",
        overall_status="advanced",
        has_sufficient_data=True,
    )
    intel_engine.get_profile = lambda dev_id: mock_profile  # type: ignore[method-assign]

    adapt = adaptation_engine.adapt_strategy("dev_learner")
    assert adapt.new_strategy == LearningStrategyType.ACCELERATED
    assert adapt.adjusted_difficulty == TaskDifficulty.ADVANCED


def test_learning_adaptation_prerequisite_first_strategy():
    _, adaptation_engine, _intel_repo, _, intel_engine = (
        _setup_feedback_and_adaptation()
    )
    mock_profile = DeveloperIntelligenceProfile(
        developer_id="dev_learner",
        overall_status="learning",
        active_gaps=["Python", "FastAPI", "SQLAlchemy", "Docker"],
        has_sufficient_data=True,
    )
    intel_engine.get_profile = lambda dev_id: mock_profile  # type: ignore[method-assign]

    adapt = adaptation_engine.adapt_strategy("dev_learner")
    assert adapt.new_strategy == LearningStrategyType.PREREQUISITE_FIRST
    assert "active knowledge gaps" in adapt.adaptation_reason
