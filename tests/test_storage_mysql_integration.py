from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from prism.config.settings import settings
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    ProficiencyLevel,
    RelationshipType,
    SkillEvidence,
    SkillRelationship,
)
from prism.learning.models import LearningProgress
from prism.storage.bootstrap import (
    check_db_connection,
    create_schema_for_test,
    drop_schema_for_test,
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


def test_mysql_developer_and_activity_lifecycle(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    act_repo = MySQLActivityRepository(session_factory, developer_repo=dev_repo)

    dev_repo.ensure_developer("dev_live_1", name="Bob Live", email="bob@prism.io")
    dev_data = dev_repo.get_developer("dev_live_1")
    assert dev_data is not None
    assert dev_data["name"] == "Bob Live"

    now = datetime.now(UTC)
    act = DeveloperActivity(
        event_id="evt_live_1",
        developer_id="dev_live_1",
        event_type="test_pass",
        timestamp=now,
        project_path="/live/prism",
        file_path="tests/test_live.py",
        metadata={"speed_ms": 42},
    )
    act_repo.save(act)

    acts = act_repo.get_by_developer("dev_live_1")
    assert len(acts) == 1
    assert acts[0].event_id == "evt_live_1"


def test_mysql_graph_and_skill_lifecycle(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    graph_repo = MySQLSkillGraphRepository(session_factory)
    skill_repo = MySQLSkillRepository(
        session_factory, developer_repo=dev_repo, graph_repo=graph_repo
    )

    graph_repo.register_skill("sk_mysql", "MySQL", category="Relational Database")
    graph_repo.register_skill("sk_sql", "SQL", category="Query Language")
    rel = SkillRelationship(
        from_skill="SQL",
        to_skill="MySQL",
        relationship_type=RelationshipType.PREREQUISITE,
    )
    graph_repo.add_relationship(rel)

    assert "MySQL" in graph_repo.get_skills()
    assert "SQL" in graph_repo.get_skills()

    now = datetime.now(UTC)
    ev = SkillEvidence(
        evidence_id="ev_live_sql",
        developer_id="dev_live_1",
        skill_name="MySQL",
        evidence_type="query_execution",
        description="Created partitioned InnoDB tables",
        timestamp=now,
    )
    skill_repo.record_evidence(ev)

    evidence_list = skill_repo.get_evidence("dev_live_1", "MySQL")
    assert len(evidence_list) == 1

    assessment = DeveloperSkill(
        developer_id="dev_live_1",
        skill_name="MySQL",
        proficiency_level=ProficiencyLevel.INTERMEDIATE,
        evidence_count=1,
        evidence_list=evidence_list,
        has_sufficient_evidence=True,
        last_assessed=now,
    )
    skill_repo.save_skill_assessment(assessment)

    profile = skill_repo.get_profile("dev_live_1")
    assert "mysql" in profile.skills
    assert profile.skills["mysql"].proficiency_level == ProficiencyLevel.INTERMEDIATE


def test_mysql_learning_progress_lifecycle(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    graph_repo = MySQLSkillGraphRepository(session_factory)
    learning_repo = MySQLLearningRepository(
        session_factory, developer_repo=dev_repo, graph_repo=graph_repo
    )

    progress = LearningProgress(
        developer_id="dev_live_1",
        target_goal="MySQL",
        completed_skills=["SQL"],
        in_progress_skills=[],
        remaining_skills=["MySQL"],
        completion_percentage=50.0,
    )
    learning_repo.save_progress(
        progress,
        path_steps=["SQL", "MySQL"],
        change_summary="Learned core SQL syntax",
    )

    retrieved = learning_repo.get_progress("dev_live_1", "MySQL")
    assert retrieved is not None
    assert retrieved.completed_skills == ["SQL"]
    assert retrieved.completion_percentage == 50.0

    history = learning_repo.get_progress_history("dev_live_1", "MySQL")
    assert len(history) == 1
    assert history[0]["completion_percentage"] == 50.0


def test_mysql_cascade_deletion(
    session_factory: sessionmaker,
    mysql_test_engine: create_engine,  # type: ignore[valid-type]
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    dev_repo.ensure_developer("dev_to_delete", name="Temporary Dev")

    with session_factory() as session:
        # Delete developer record
        session.execute(
            text("DELETE FROM developers WHERE developer_id = 'dev_to_delete'")
        )
        session.commit()

    assert dev_repo.get_developer("dev_to_delete") is None
