"""MySQL Persistence Integration Tests for Phase 19 Intelligence Entities."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from prism.config.settings import settings
from prism.intelligence.models.developer_intelligence_models import (
    DeveloperFeedback,
    DeveloperInsight,
    DeveloperPerformanceSnapshot,
    FeedbackCategory,
    InsightCategory,
    InsightSeverity,
    LearningAdaptation,
    LearningStrategyType,
    PersonalizedTask,
    TaskDifficulty,
    TaskOutcome,
    TaskPriority,
    TaskStatus,
)
from prism.mentoring.models import MentoringSessionRecord, MentoringStrategy
from prism.storage.bootstrap import (
    check_db_connection,
    create_schema_for_test,
    drop_schema_for_test,
)
from prism.storage.repositories.mysql_developer_repo import (
    MySQLDeveloperRepository,
)
from prism.storage.repositories.mysql_intelligence_repo import (
    MySQLIntelligenceRepository,
)


def is_mysql_test_server_live() -> bool:
    try:
        engine = create_engine(settings.test_database_url, pool_pre_ping=True)
        return check_db_connection(engine)
    except SQLAlchemyError, OSError:
        return False


pytestmark = pytest.mark.skipif(
    not is_mysql_test_server_live(),
    reason="Live MySQL test server is offline or unreachable at test_database_url",
)


@pytest.fixture(scope="module")
def mysql_test_engine() -> Generator[create_engine]:  # type: ignore[valid-type]
    engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    create_schema_for_test(engine)
    try:
        yield engine
    finally:
        drop_schema_for_test(engine)


@pytest.fixture
def session_factory(mysql_test_engine: create_engine) -> sessionmaker:  # type: ignore[valid-type]
    return sessionmaker(bind=mysql_test_engine, expire_on_commit=False)


def test_mysql_intelligence_insights_persistence(session_factory: sessionmaker):
    dev_repo = MySQLDeveloperRepository(session_factory)
    intel_repo = MySQLIntelligenceRepository(session_factory)

    dev_id = f"dev_sql_ins_{uuid.uuid4().hex[:6]}"
    dev_repo.create_developer(
        dev_id, name="Insight Tester", email=f"{dev_id}@prism.dev"
    )

    now = datetime.now(UTC)
    insight = DeveloperInsight(
        insight_id=f"ins_{uuid.uuid4().hex[:8]}",
        developer_id=dev_id,
        category=InsightCategory.STRENGTH,
        severity=InsightSeverity.INFO,
        title="Python Mastery",
        description="Exceptional performance in Python asynchronous workflows.",
        actionable_recommendation="Mentor junior developers on concurrency.",
        timestamp=now,
    )
    intel_repo.save_insight(insight)

    insights = intel_repo.get_insights(dev_id)
    assert len(insights) >= 1
    assert insights[0].title == "Python Mastery"


def test_mysql_performance_snapshots_persistence(session_factory: sessionmaker):
    dev_repo = MySQLDeveloperRepository(session_factory)
    intel_repo = MySQLIntelligenceRepository(session_factory)

    dev_id = f"dev_sql_snp_{uuid.uuid4().hex[:6]}"
    dev_repo.create_developer(
        dev_id, name="Snapshot Tester", email=f"{dev_id}@prism.dev"
    )

    now = datetime.now(UTC)
    snap = DeveloperPerformanceSnapshot(
        snapshot_id=f"snp_{uuid.uuid4().hex[:8]}",
        developer_id=dev_id,
        timestamp=now,
        total_activities=12,
        verified_skills_count=4,
        average_proficiency_score=82.5,
        active_knowledge_gaps_count=2,
        tasks_completed_count=3,
        task_success_rate=1.0,
        learning_consistency_score=0.9,
        role_readiness_scores={"backend_developer": 0.85},
    )
    intel_repo.save_snapshot(snap)

    latest = intel_repo.get_latest_snapshot(dev_id)
    assert latest is not None
    assert latest.snapshot_id == snap.snapshot_id
    assert latest.average_proficiency_score == 82.5
    assert latest.role_readiness_scores.get("backend_developer") == 0.85


def test_mysql_tasks_and_outcomes_persistence(session_factory: sessionmaker):
    dev_repo = MySQLDeveloperRepository(session_factory)
    intel_repo = MySQLIntelligenceRepository(session_factory)

    dev_id = f"dev_sql_tsk_{uuid.uuid4().hex[:6]}"
    dev_repo.create_developer(dev_id, name="Task Tester", email=f"{dev_id}@prism.dev")

    now = datetime.now(UTC)
    task_id = f"tsk_{uuid.uuid4().hex[:8]}"
    task = PersonalizedTask(
        task_id=task_id,
        developer_id=dev_id,
        title="Implement Rate Limiter",
        description="Build a sliding window rate limiter in Redis",
        target_skill="Redis",
        difficulty=TaskDifficulty.INTERMEDIATE,
        priority=TaskPriority.HIGH,
        status=TaskStatus.GENERATED,
        estimated_minutes=45,
        target_role="backend_developer",
        reason="Close Redis caching gap",
        created_at=now,
        updated_at=now,
    )
    intel_repo.save_task(task)

    fetched = intel_repo.get_task(task_id)
    assert fetched is not None
    assert fetched.title == "Implement Rate Limiter"

    # Update status
    updated = intel_repo.update_task_status(task_id, "in_progress")
    assert updated is not None
    assert updated.status == TaskStatus.IN_PROGRESS

    # Save outcome
    outcome = TaskOutcome(
        outcome_id=f"out_{uuid.uuid4().hex[:8]}",
        task_id=task_id,
        developer_id=dev_id,
        success=True,
        execution_notes="Passed benchmark with 5000 req/sec",
        verified_artifacts=["redis_limiter.py"],
        recorded_at=now,
    )
    intel_repo.save_task_outcome(outcome)

    outcomes = intel_repo.get_task_outcomes(dev_id)
    assert len(outcomes) == 1
    assert outcomes[0].success is True


def test_mysql_feedback_mentoring_and_adaptation_persistence(
    session_factory: sessionmaker,
):
    dev_repo = MySQLDeveloperRepository(session_factory)
    intel_repo = MySQLIntelligenceRepository(session_factory)

    dev_id = f"dev_sql_fma_{uuid.uuid4().hex[:6]}"
    dev_repo.create_developer(dev_id, name="FMA Tester", email=f"{dev_id}@prism.dev")

    now = datetime.now(UTC)

    # 1. Feedback
    fb = DeveloperFeedback(
        feedback_id=f"fb_{uuid.uuid4().hex[:8]}",
        developer_id=dev_id,
        category=FeedbackCategory.POSITIVE,
        message="Great job optimizing the data pipeline!",
        supporting_evidence=["Reduced query time by 40%"],
        recommended_next_action="Deploy changes to staging.",
        timestamp=now,
    )
    intel_repo.save_feedback(fb)
    feedbacks = intel_repo.get_feedbacks(dev_id)
    assert len(feedbacks) >= 1
    assert feedbacks[0].category == FeedbackCategory.POSITIVE

    # 2. Mentoring Session
    session_rec = MentoringSessionRecord(
        session_id=f"ms_{uuid.uuid4().hex[:8]}",
        developer_id=dev_id,
        strategy=MentoringStrategy.GUIDED_IMPLEMENTATION,
        query="How to structure repository layer",
        summary="Guided discussion on Repository pattern",
        outcome_rating=5.0,
        created_at=now,
    )
    intel_repo.save_mentoring_session(session_rec)
    sessions = intel_repo.get_mentoring_sessions(dev_id)
    assert len(sessions) >= 1
    assert sessions[0].outcome_rating == 5.0

    # 3. Learning Adaptation
    adaptation = LearningAdaptation(
        adaptation_id=f"adp_{uuid.uuid4().hex[:8]}",
        developer_id=dev_id,
        previous_strategy="standard",
        new_strategy=LearningStrategyType.PRACTICE_INTENSIVE,
        adaptation_reason="Detected stagnation in FastAPI",
        adjusted_difficulty=TaskDifficulty.INTERMEDIATE,
        adjusted_priorities={"FastAPI": "High priority"},
        stalled_skills_detected=["FastAPI"],
        timestamp=now,
    )
    intel_repo.save_adaptation(adaptation)
    latest_adp = intel_repo.get_latest_adaptation(dev_id)
    assert latest_adp is not None
    assert latest_adp.new_strategy == LearningStrategyType.PRACTICE_INTENSIVE
    assert "FastAPI" in latest_adp.stalled_skills_detected
