from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from prism.config.settings import settings
from prism.intelligence.models.developer_behavior_models import DeveloperActivity
from prism.intelligence.models.developer_identity_models import (
    DeveloperSession,
    SessionStatus,
)
from prism.storage.bootstrap import (
    check_db_connection,
    create_schema_for_test,
    drop_schema_for_test,
)
from prism.storage.database import session_scope
from prism.storage.models.developer_records import DeveloperRecord
from prism.storage.models.session_records import DeveloperSessionRecord
from prism.storage.repositories.mysql_activity_repo import (
    MySQLActivityRepository,
)
from prism.storage.repositories.mysql_developer_repo import (
    MySQLDeveloperRepository,
)
from prism.storage.repositories.mysql_session_repo import MySQLSessionRepository


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


def test_mysql_developer_repo_crud_and_uniqueness(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)

    # Create developer
    dev = dev_repo.create_developer(
        developer_id="dev_mysql_1",
        name="MySQL Alice",
        email="alice_mysql@prism.io",
    )
    assert dev["developer_id"] == "dev_mysql_1"
    assert dev["name"] == "MySQL Alice"
    assert dev["email"] == "alice_mysql@prism.io"

    # Get by ID
    fetched = dev_repo.get_developer("dev_mysql_1")
    assert fetched is not None
    assert fetched["name"] == "MySQL Alice"

    # Get by Email
    by_email = dev_repo.get_by_email("alice_mysql@prism.io")
    assert by_email is not None
    assert by_email["developer_id"] == "dev_mysql_1"

    # Reject duplicate ID
    with pytest.raises(ValueError, match="already exists"):
        dev_repo.create_developer("dev_mysql_1", name="Other")

    # Reject duplicate Email
    with pytest.raises(ValueError, match="already exists"):
        dev_repo.create_developer("dev_mysql_2", email="alice_mysql@prism.io")

    # Update developer
    updated = dev_repo.update_developer(
        "dev_mysql_1", name="Alice Updated", email="alice_new@prism.io"
    )
    assert updated is not None
    assert updated["name"] == "Alice Updated"
    assert updated["email"] == "alice_new@prism.io"


def test_mysql_session_lifecycle(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    ses_repo = MySQLSessionRepository(session_factory, developer_repo=dev_repo)

    dev_repo.ensure_developer("dev_ses_sql", name="Session Dev")

    now = datetime.now(UTC)
    session = DeveloperSession(
        session_id="ses_mysql_live_1",
        developer_id="dev_ses_sql",
        status=SessionStatus.ACTIVE.value,
        started_at=now,
        last_activity_at=now,
        ended_at=None,
        project_path="/live/repo",
        metadata={"os": "linux"},
        created_at=now,
        updated_at=now,
    )
    ses_repo.create_session(session)

    # Verify session persisted
    retrieved = ses_repo.get_session("ses_mysql_live_1")
    assert retrieved is not None
    assert retrieved.developer_id == "dev_ses_sql"
    assert retrieved.status == "active"
    assert retrieved.metadata.get("os") == "linux"

    # Verify active session query
    active = ses_repo.get_active_session("dev_ses_sql")
    assert active is not None
    assert active.session_id == "ses_mysql_live_1"

    # Touch heartbeat
    heartbeat_time = now + timedelta(seconds=10)
    touched = ses_repo.touch_heartbeat(
        "ses_mysql_live_1", heartbeat_time, metadata={"keystrokes": 42}
    )
    assert touched is True

    reloaded_after_hb = ses_repo.get_session("ses_mysql_live_1")
    assert reloaded_after_hb is not None
    assert reloaded_after_hb.metadata.get("keystrokes") == 42

    # Terminate session
    end_time = now + timedelta(minutes=10)
    terminated = ses_repo.terminate_session(
        "ses_mysql_live_1", SessionStatus.COMPLETED.value, end_time
    )
    assert terminated is True

    # Active session should now be None
    assert ses_repo.get_active_session("dev_ses_sql") is None


def test_mysql_session_history_pagination(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    ses_repo = MySQLSessionRepository(session_factory, developer_repo=dev_repo)
    dev_repo.ensure_developer("dev_hist_sql", name="Hist Dev")

    base_time = datetime.now(UTC)
    for i in range(5):
        s = DeveloperSession(
            session_id=f"ses_hist_{i}",
            developer_id="dev_hist_sql",
            status="completed",
            started_at=base_time + timedelta(minutes=i),
            last_activity_at=base_time + timedelta(minutes=i + 5),
            ended_at=base_time + timedelta(minutes=i + 5),
            project_path="/proj/hist",
            metadata={},
            created_at=base_time,
            updated_at=base_time,
        )
        ses_repo.create_session(s)

    # Page 1: limit 2, offset 0
    page1, total = ses_repo.list_sessions_for_developer(
        "dev_hist_sql", limit=2, offset=0
    )
    assert total == 5
    assert len(page1) == 2
    # Ordered descending by started_at -> ses_hist_4 first
    assert page1[0].session_id == "ses_hist_4"

    # Page 2: limit 2, offset 2
    page2, _ = ses_repo.list_sessions_for_developer("dev_hist_sql", limit=2, offset=2)
    assert len(page2) == 2
    assert page2[0].session_id == "ses_hist_2"


def test_mysql_session_foreign_key_cascade(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    ses_repo = MySQLSessionRepository(session_factory, developer_repo=dev_repo)

    dev_repo.ensure_developer("dev_cascade_ses", name="Cascade Dev")
    now = datetime.now(UTC)
    ses = DeveloperSession(
        session_id="ses_cascade_target",
        developer_id="dev_cascade_ses",
        status="active",
        started_at=now,
        last_activity_at=now,
        ended_at=None,
        project_path="/proj",
        metadata={},
        created_at=now,
        updated_at=now,
    )
    ses_repo.create_session(ses)
    assert ses_repo.get_session("ses_cascade_target") is not None

    # Delete developer record directly from DB
    with session_scope(session_factory) as session:
        stmt = select(DeveloperRecord).where(
            DeveloperRecord.developer_id == "dev_cascade_ses"
        )
        dev = session.scalar(stmt)
        if dev:
            session.delete(dev)

    # Verify session was cascaded and removed
    with session_scope(session_factory) as session:
        ses_stmt = select(DeveloperSessionRecord).where(
            DeveloperSessionRecord.session_id == "ses_cascade_target"
        )
        assert session.scalar(ses_stmt) is None


def test_mysql_activity_session_association(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    ses_repo = MySQLSessionRepository(session_factory, developer_repo=dev_repo)
    act_repo = MySQLActivityRepository(session_factory, developer_repo=dev_repo)

    dev_repo.ensure_developer("dev_act_ses", name="Act Ses Dev")
    now = datetime.now(UTC)

    ses = DeveloperSession(
        session_id="ses_associated_1",
        developer_id="dev_act_ses",
        status="active",
        started_at=now,
        last_activity_at=now,
        ended_at=None,
        project_path="/proj/test",
        metadata={},
        created_at=now,
        updated_at=now,
    )
    ses_repo.create_session(ses)

    # Save activities associated with this session
    act1 = DeveloperActivity(
        event_id="evt_ses_1",
        developer_id="dev_act_ses",
        session_id="ses_associated_1",
        event_type="file_open",
        timestamp=now,
        project_path="/proj/test",
    )
    act2 = DeveloperActivity(
        event_id="evt_ses_2",
        developer_id="dev_act_ses",
        session_id="ses_associated_1",
        event_type="code_edit",
        timestamp=now + timedelta(seconds=5),
        project_path="/proj/test",
    )
    act_other = DeveloperActivity(
        event_id="evt_ses_other",
        developer_id="dev_act_ses",
        session_id="ses_other_id",
        event_type="test_run",
        timestamp=now + timedelta(seconds=10),
        project_path="/proj/test",
    )
    act_repo.save_many([act1, act2, act_other])

    # Query activities by session
    session_acts = act_repo.get_by_session("ses_associated_1")
    assert len(session_acts) == 2
    assert {a.event_id for a in session_acts} == {"evt_ses_1", "evt_ses_2"}


def test_mysql_persistence_across_new_session_factory(
    mysql_test_engine: create_engine,  # type: ignore[valid-type]
) -> None:
    # Factory 1 writes
    factory1 = sessionmaker(bind=mysql_test_engine, expire_on_commit=False)
    dev_repo1 = MySQLDeveloperRepository(factory1)
    ses_repo1 = MySQLSessionRepository(factory1, developer_repo=dev_repo1)

    dev_repo1.create_developer("dev_restart_test", name="Restart User")
    now = datetime.now(UTC)
    ses_repo1.create_session(
        DeveloperSession(
            session_id="ses_restart_persisted",
            developer_id="dev_restart_test",
            status="active",
            started_at=now,
            last_activity_at=now,
            ended_at=None,
            project_path="/restart/path",
            metadata={"persisted": True},
            created_at=now,
            updated_at=now,
        )
    )

    # Factory 2 reads (simulating application restart)
    factory2 = sessionmaker(bind=mysql_test_engine, expire_on_commit=False)
    dev_repo2 = MySQLDeveloperRepository(factory2)
    ses_repo2 = MySQLSessionRepository(factory2, developer_repo=dev_repo2)

    dev_fetched = dev_repo2.get_developer("dev_restart_test")
    assert dev_fetched is not None
    assert dev_fetched["name"] == "Restart User"

    ses_fetched = ses_repo2.get_session("ses_restart_persisted")
    assert ses_fetched is not None
    assert ses_fetched.metadata.get("persisted") is True


def test_mysql_stale_sessions_and_cleanup(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    ses_repo = MySQLSessionRepository(session_factory, developer_repo=dev_repo)
    dev_repo.ensure_developer("dev_stale_sql", name="Stale Dev")

    old_time = datetime.now(UTC) - timedelta(hours=2)
    now = datetime.now(UTC)

    stale_ses = DeveloperSession(
        session_id="ses_stale_1",
        developer_id="dev_stale_sql",
        status="active",
        started_at=old_time,
        last_activity_at=old_time,
        ended_at=None,
        project_path="/proj/stale",
        metadata={},
        created_at=old_time,
        updated_at=old_time,
    )
    fresh_ses = DeveloperSession(
        session_id="ses_fresh_1",
        developer_id="dev_stale_sql",
        status="active",
        started_at=now,
        last_activity_at=now,
        ended_at=None,
        project_path="/proj/fresh",
        metadata={},
        created_at=now,
        updated_at=now,
    )
    ses_repo.create_session(stale_ses)
    ses_repo.create_session(fresh_ses)

    cutoff = datetime.now(UTC) - timedelta(minutes=30)
    stale_list = ses_repo.get_stale_sessions(cutoff)
    stale_ids = [s.session_id for s in stale_list]
    assert "ses_stale_1" in stale_ids
    assert "ses_fresh_1" not in stale_ids


def test_mysql_touch_heartbeat_without_metadata_and_update_session(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    ses_repo = MySQLSessionRepository(session_factory, developer_repo=dev_repo)
    dev_repo.ensure_developer("dev_hb_sql", name="HB Dev")

    now = datetime.now(UTC)
    ses = DeveloperSession(
        session_id="ses_hb_no_meta",
        developer_id="dev_hb_sql",
        status="active",
        started_at=now,
        last_activity_at=now,
        ended_at=None,
        project_path="/proj/hb",
        metadata={"orig": True},
        created_at=now,
        updated_at=now,
    )
    ses_repo.create_session(ses)

    # Touch heartbeat without extra metadata
    new_time = now + timedelta(minutes=1)
    ok = ses_repo.touch_heartbeat("ses_hb_no_meta", new_time)
    assert ok is True

    # Touch non-existent session
    assert ses_repo.touch_heartbeat("ses_does_not_exist", new_time) is False

    # Update session
    ses.status = "completed"
    ses.ended_at = new_time
    ses_repo.update_session(ses)

    reloaded = ses_repo.get_session("ses_hb_no_meta")
    assert reloaded is not None
    assert reloaded.status == "completed"

    # Clear sessions for developer
    ses_repo.clear("dev_hb_sql")
    assert ses_repo.get_session("ses_hb_no_meta") is None
