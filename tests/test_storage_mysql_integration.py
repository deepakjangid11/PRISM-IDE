from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from prism.api.dependencies import init_storage_repositories
from prism.config.settings import settings
from prism.exceptions.custom_exception import CustomException
from prism.intelligence.developer_activity import ActivityRecorder
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
from prism.intelligence.skill_graph import SkillGraph
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.models import LearningPath, LearningProgress
from prism.learning.progress_tracker import LearningProgressTracker
from prism.storage.bootstrap import (
    check_db_connection,
    create_schema_for_test,
    drop_schema_for_test,
)
from prism.storage.database import session_scope
from prism.storage.models.activity_records import DeveloperActivityRecord
from prism.storage.models.developer_records import DeveloperRecord
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
from prism.storage.seeder import (
    DEFAULT_RELATIONSHIPS,
    DEFAULT_SKILLS,
    seed_default_curriculum,
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


def test_mysql_developer_and_activity_lifecycle(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    act_repo = MySQLActivityRepository(session_factory, developer_repo=dev_repo)

    dev_repo.ensure_developer("dev_live_1", name="Bob Live", email="bob@prism.io")
    dev_data = dev_repo.get_developer("dev_live_1")
    assert dev_data is not None
    assert dev_data["name"] == "Bob Live"
    assert "dev_live_1" in dev_repo.list_developers()

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


def test_mysql_activity_save_many_and_filtering(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    act_repo = MySQLActivityRepository(session_factory, developer_repo=dev_repo)
    now = datetime.now(UTC)

    acts = [
        DeveloperActivity(
            event_id=f"batch_evt_{i}",
            developer_id="dev_batch",
            event_type="code_edit",
            timestamp=now,
            project_path="/repo/project_a" if i % 2 == 0 else "/repo/project_b",
            file_path=f"src/file_{i}.py",
        )
        for i in range(4)
    ]
    act_repo.save_many(acts)

    all_batch = act_repo.get_by_developer("dev_batch")
    assert len(all_batch) == 4

    filtered = act_repo.get_by_developer("dev_batch", project_path="/repo/project_a")
    assert len(filtered) == 2


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
    assert history[0]["change_summary"] == "Learned core SQL syntax"


def test_mysql_seeder_idempotency(
    session_factory: sessionmaker,
) -> None:
    graph_repo = MySQLSkillGraphRepository(session_factory)

    # First run
    seed_default_curriculum(graph_repo)
    skills = graph_repo.get_skills()
    rels = graph_repo.get_relationships()
    assert len(skills) >= len(DEFAULT_SKILLS)
    assert len(rels) >= len(DEFAULT_RELATIONSHIPS)

    # Second run must not fail or duplicate
    seed_default_curriculum(graph_repo)
    skills2 = graph_repo.get_skills()
    rels2 = graph_repo.get_relationships()
    assert len(skills2) == len(skills)
    assert len(rels2) == len(rels)


def test_mysql_transaction_rollback(
    session_factory: sessionmaker,
) -> None:
    with pytest.raises(CustomException), session_scope(session_factory) as session:
        record = DeveloperRecord(
            developer_id="dev_rollback_test",
            name="Should Roll Back",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(record)
        session.flush()
        # Force simulated error inside transaction
        raise RuntimeError("Simulated failure to verify transaction rollback")

    # Verify record was not committed to database
    with session_factory() as verify_session:
        stmt = select(DeveloperRecord).where(
            DeveloperRecord.developer_id == "dev_rollback_test"
        )
        found = verify_session.scalar(stmt)
        assert found is None


def test_mysql_cascade_deletion(
    session_factory: sessionmaker,
    mysql_test_engine: create_engine,  # type: ignore[valid-type]
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    act_repo = MySQLActivityRepository(session_factory, developer_repo=dev_repo)

    dev_repo.ensure_developer("dev_to_delete", name="Temporary Dev")
    act = DeveloperActivity(
        event_id="evt_delete_test",
        developer_id="dev_to_delete",
        event_type="git_push",
        timestamp=datetime.now(UTC),
        project_path="/tmp/prism",
    )
    act_repo.save(act)

    with session_factory() as session:
        # Delete master developer record
        session.execute(
            text("DELETE FROM developers WHERE developer_id = 'dev_to_delete'")
        )
        session.commit()

    assert dev_repo.get_developer("dev_to_delete") is None
    # Activities referencing this developer must be cascaded
    with session_factory() as session:
        act_stmt = select(DeveloperActivityRecord).where(
            DeveloperActivityRecord.developer_id == "dev_to_delete"
        )
        assert session.scalar(act_stmt) is None


def test_mysql_persistence_across_restart(
    session_factory: sessionmaker,
    mysql_test_engine: create_engine,  # type: ignore[valid-type]
) -> None:
    # 1. First "session" writes data
    dev_repo1 = MySQLDeveloperRepository(session_factory)
    dev_repo1.ensure_developer(
        "dev_persist", name="Persistent Dev", email="persist@prism.io"
    )

    # 2. Simulate application restart: create a completely new sessionmaker factory
    new_factory = sessionmaker(bind=mysql_test_engine, expire_on_commit=False)
    dev_repo2 = MySQLDeveloperRepository(new_factory)

    # 3. Read data from fresh factory
    loaded = dev_repo2.get_developer("dev_persist")
    assert loaded is not None
    assert loaded["name"] == "Persistent Dev"
    assert loaded["email"] == "persist@prism.io"


def test_production_safety_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate database connectivity failure in MySQL mode
    monkeypatch.setattr("prism.api.dependencies.check_db_connection", lambda: False)

    # In production mysql mode, failure MUST raise RuntimeError, never silently switch
    with pytest.raises(RuntimeError, match="Silent in-memory fallback is disabled"):
        init_storage_repositories("mysql")


def test_explicit_memory_configuration() -> None:
    # Explicit memory backend provisions in-memory repositories cleanly
    repos = init_storage_repositories("memory")
    assert len(repos) == 6
    dev_repo, _act, _grp, _skl, _lrn, _ses = repos

    dev_repo.ensure_developer("dev_mem", name="Memory Dev")
    assert dev_repo.get_developer("dev_mem") is not None


def test_mysql_api_health_endpoint() -> None:
    from fastapi.testclient import TestClient

    from prism.api.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_mysql_services_end_to_end_integration(
    session_factory: sessionmaker,
) -> None:
    # Wire domain services to live MySQL repositories
    dev_repo = MySQLDeveloperRepository(session_factory)
    act_repo = MySQLActivityRepository(session_factory, developer_repo=dev_repo)
    grp_repo = MySQLSkillGraphRepository(session_factory)
    skl_repo = MySQLSkillRepository(
        session_factory, developer_repo=dev_repo, graph_repo=grp_repo
    )
    lrn_repo = MySQLLearningRepository(
        session_factory, developer_repo=dev_repo, graph_repo=grp_repo
    )

    recorder = ActivityRecorder(repository=act_repo)
    tracker = SkillTracker(repository=skl_repo, developer_repo=dev_repo)
    graph = SkillGraph(repository=grp_repo)
    progress_tracker = LearningProgressTracker(repository=lrn_repo)

    now = datetime.now(UTC)
    dev_id = "dev_e2e_service"

    # 1. Activity recorder persists to MySQL
    recorder.record(
        DeveloperActivity(
            event_id="e2e_act_1",
            developer_id=dev_id,
            event_type="git_commit",
            timestamp=now,
            project_path="/srv/prism",
        )
    )
    dev_acts = recorder.get_activities_for_developer(dev_id)
    assert len(dev_acts) == 1

    # 2. Graph adds skills and relationships to MySQL
    graph.add_skill("Python")
    graph.add_skill("FastAPI")
    graph.add_relationship("Python", "FastAPI", RelationshipType.PREREQUISITE)
    assert "FastAPI" in graph.get_dependents("Python")

    # 3. Skill tracker records evidence and persists assessment to MySQL
    for i in range(3):
        tracker.record_evidence(
            SkillEvidence(
                evidence_id=f"e2e_ev_{i}",
                developer_id=dev_id,
                skill_name="Python",
                evidence_type="code_artifact",
                description=f"Unit test {i}",
                timestamp=now,
            )
        )
    dev_profile = tracker.get_profile(dev_id)
    assert dev_profile.skills["python"].evidence_count == 3
    assert dev_profile.skills["python"].proficiency_level == ProficiencyLevel.BEGINNER

    # 4. Learning progress tracker evaluates and persists roadmap to MySQL
    learning_path = LearningPath(
        path_id="e2e_path_1",
        developer_id=dev_id,
        target_goal="FastAPI",
        steps=["Python", "FastAPI"],
        estimated_steps=2,
    )
    prog = progress_tracker.track_progress(dev_profile, learning_path)
    assert prog.completed_skills == ["Python"]
    assert prog.remaining_skills == ["FastAPI"]
    assert prog.completion_percentage == 50.0

    # 5. Verify retrieval from MySQL through progress_tracker
    retrieved = progress_tracker.get_progress(dev_id, "FastAPI")
    assert retrieved is not None
    assert retrieved.completed_skills == ["Python"]

    hist = progress_tracker.get_progress_history(dev_id, "FastAPI")
    assert len(hist) == 1
    assert hist[0]["completion_percentage"] == 50.0
