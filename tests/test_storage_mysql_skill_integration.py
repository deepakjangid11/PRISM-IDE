from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from prism.config.settings import settings
from prism.intelligence.models.developer_behavior_models import DeveloperActivity
from prism.intelligence.models.skill_models import (
    ProficiencyLevel,
    SkillEvidence,
)
from prism.intelligence.skill_evidence_engine import SkillEvidenceEngine
from prism.intelligence.skill_tracker import SkillTracker
from prism.storage.bootstrap import (
    check_db_connection,
    create_schema_for_test,
    drop_schema_for_test,
)
from prism.storage.repositories.mysql_developer_repo import (
    MySQLDeveloperRepository,
)
from prism.storage.repositories.mysql_graph_repo import MySQLSkillGraphRepository
from prism.storage.repositories.mysql_skill_repo import MySQLSkillRepository


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


def test_mysql_skill_evidence_rich_attributes_persistence(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    graph_repo = MySQLSkillGraphRepository(session_factory)
    skill_repo = MySQLSkillRepository(
        session_factory, developer_repo=dev_repo, graph_repo=graph_repo
    )

    dev_id = "dev_sql_rich"
    dev_repo.ensure_developer(dev_id, name="Rich Dev", email="rich@prism.io")

    now = datetime.now(UTC)
    evidence = SkillEvidence(
        evidence_id="ev_sql_1",
        developer_id=dev_id,
        skill_name="FastAPI",
        skill_id="fastapi",
        evidence_type="implementation",
        description="Built async websocket endpoint",
        project_path="/srv/prism",
        programming_language="Python",
        framework="FastAPI",
        evidence_source="activity_stream",
        evidence_strength=1.3,
        confidence_score=0.92,
        complexity_score=0.85,
        related_activity_id="act_sql_101",
        timestamp=now,
    )

    skill_repo.record_evidence(evidence)

    retrieved = skill_repo.get_evidence(dev_id, skill_name="FastAPI")
    assert len(retrieved) == 1
    ev = retrieved[0]
    assert ev.evidence_id == "ev_sql_1"
    assert ev.developer_id == dev_id
    assert ev.skill_name == "FastAPI"
    assert ev.programming_language == "Python"
    assert ev.framework == "FastAPI"
    assert ev.evidence_source == "activity_stream"
    assert ev.evidence_strength == 1.3
    assert ev.confidence_score == 0.92
    assert ev.complexity_score == 0.85
    assert ev.related_activity_id == "act_sql_101"


def test_mysql_skill_tracker_and_evidence_engine_e2e(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    graph_repo = MySQLSkillGraphRepository(session_factory)
    skill_repo = MySQLSkillRepository(
        session_factory, developer_repo=dev_repo, graph_repo=graph_repo
    )

    tracker = SkillTracker(repository=skill_repo, developer_repo=dev_repo)
    engine = SkillEvidenceEngine(skill_tracker=tracker)

    dev_id = "dev_sql_tracker"
    dev_repo.ensure_developer(dev_id, name="Tracker Dev", email="tracker@prism.io")

    # Ingest 3 distinct activities via SkillEvidenceEngine
    for i in range(1, 4):
        act = DeveloperActivity(
            event_id=f"act_sql_tr_{i}",
            developer_id=dev_id,
            event_type="function_create",
            project_path=f"/repo_{i}",
            file_path=f"src/module_{i}.py",
            timestamp=datetime.now(UTC),
            metadata={
                "classification": {
                    "language": "Python",
                    "framework": "SQLAlchemy",
                    "complexity_estimate": "medium",
                }
            },
        )
        engine.process_activity(act)

    profile = tracker.get_profile(dev_id)
    assert profile.developer_id == dev_id
    assert "python" in profile.skills
    assert profile.skills["python"].evidence_count == 3
    assert profile.skills["python"].proficiency_level == ProficiencyLevel.BEGINNER
    assert profile.skills["python"].proficiency_score > 0
    assert profile.skills["python"].has_sufficient_evidence
