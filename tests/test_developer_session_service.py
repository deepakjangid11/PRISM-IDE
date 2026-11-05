from datetime import UTC, datetime, timedelta

import pytest

from prism.config.settings import Settings
from prism.intelligence.developer_activity import ActivityRecorder
from prism.intelligence.developer_session import DeveloperSessionService
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.developer_identity_models import (
    SessionStatus,
)
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemorySessionRepository,
)


@pytest.fixture
def repos() -> tuple[
    InMemoryDeveloperRepository,
    InMemorySessionRepository,
    InMemoryActivityRepository,
]:
    dev_repo = InMemoryDeveloperRepository()
    dev_repo.ensure_developer(
        "dev_tester", name="Session Tester", email="tester@prism.io"
    )
    dev_repo.ensure_developer("dev_other", name="Other Dev", email="other@prism.io")
    ses_repo = InMemorySessionRepository(dev_repo=dev_repo)
    act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    return dev_repo, ses_repo, act_repo


@pytest.fixture
def session_service(
    repos: tuple[
        InMemoryDeveloperRepository,
        InMemorySessionRepository,
        InMemoryActivityRepository,
    ],
) -> DeveloperSessionService:
    dev_repo, ses_repo, _ = repos
    test_settings = Settings(session_timeout_minutes=15)
    return DeveloperSessionService(
        session_repo=ses_repo,
        developer_repo=dev_repo,
        app_settings=test_settings,
    )


def test_start_session_lifecycle(
    session_service: DeveloperSessionService,
) -> None:
    session = session_service.start_session(
        developer_id="dev_tester",
        project_path="/projects/prism",
        metadata={"client": "vscode"},
    )

    assert session.session_id.startswith("ses_")
    assert session.developer_id == "dev_tester"
    assert session.project_path == "/projects/prism"
    assert session.status == SessionStatus.ACTIVE.value
    assert session.is_active is True
    assert session.ended_at is None
    assert session.metadata["client"] == "vscode"


def test_start_session_unknown_developer_fails(
    session_service: DeveloperSessionService,
) -> None:
    with pytest.raises(ValueError, match="Developer not found"):
        session_service.start_session(developer_id="dev_nonexistent")


def test_single_active_session_enforcement(
    session_service: DeveloperSessionService,
) -> None:
    ses1 = session_service.start_session(developer_id="dev_tester")
    assert ses1.status == SessionStatus.ACTIVE.value

    # Starting second session concludes previous session
    ses2 = session_service.start_session(developer_id="dev_tester")
    assert ses2.status == SessionStatus.ACTIVE.value
    assert ses2.session_id != ses1.session_id

    # Verify first session was marked completed
    reloaded_ses1 = session_service.session_repo.get_session(ses1.session_id)
    assert reloaded_ses1 is not None
    assert reloaded_ses1.status == SessionStatus.COMPLETED.value
    assert reloaded_ses1.ended_at is not None

    # Current active session is ses2
    current_active = session_service.get_active_session("dev_tester")
    assert current_active is not None
    assert current_active.session_id == ses2.session_id


def test_session_heartbeat(
    session_service: DeveloperSessionService,
) -> None:
    ses = session_service.start_session(developer_id="dev_tester")
    orig_activity = ses.last_activity_at

    updated = session_service.send_heartbeat(
        session_id=ses.session_id,
        developer_id="dev_tester",
        metadata={"typing_speed": 120},
    )

    assert updated.session_id == ses.session_id
    assert updated.last_activity_at >= orig_activity
    assert updated.metadata.get("typing_speed") == 120


def test_session_heartbeat_ownership_validation(
    session_service: DeveloperSessionService,
) -> None:
    ses = session_service.start_session(developer_id="dev_tester")

    with pytest.raises(ValueError, match="does not belong to developer"):
        session_service.send_heartbeat(
            session_id=ses.session_id,
            developer_id="dev_other",
        )


def test_session_heartbeat_on_completed_session_rejected(
    session_service: DeveloperSessionService,
) -> None:
    ses = session_service.start_session(developer_id="dev_tester")
    session_service.end_session(ses.session_id, "dev_tester")

    with pytest.raises(ValueError, match="Cannot heartbeat session"):
        session_service.send_heartbeat(
            session_id=ses.session_id,
            developer_id="dev_tester",
        )


def test_session_heartbeat_on_stale_session(
    session_service: DeveloperSessionService,
) -> None:
    ses = session_service.start_session(developer_id="dev_tester")

    # Manually age the session beyond 15 min timeout
    old_time = datetime.now(UTC) - timedelta(minutes=20)
    session_service.session_repo.touch_heartbeat(ses.session_id, old_time)

    with pytest.raises(ValueError, match="Session .* has expired due to inactivity"):
        session_service.send_heartbeat(
            session_id=ses.session_id,
            developer_id="dev_tester",
        )

    # Session is transitioned to stale state
    reloaded = session_service.session_repo.get_session(ses.session_id)
    assert reloaded is not None
    assert reloaded.status == SessionStatus.STALE.value


def test_end_session(
    session_service: DeveloperSessionService,
) -> None:
    ses = session_service.start_session(developer_id="dev_tester")
    ended = session_service.end_session(
        session_id=ses.session_id,
        developer_id="dev_tester",
        status=SessionStatus.TERMINATED.value,
    )

    assert ended.status == SessionStatus.TERMINATED.value
    assert ended.ended_at is not None

    # Idempotent repeated termination does not throw
    repeated = session_service.end_session(
        session_id=ses.session_id,
        developer_id="dev_tester",
    )
    assert repeated.status == SessionStatus.TERMINATED.value


def test_end_session_ownership_validation(
    session_service: DeveloperSessionService,
) -> None:
    ses = session_service.start_session(developer_id="dev_tester")
    with pytest.raises(ValueError, match="does not belong to developer"):
        session_service.end_session(session_id=ses.session_id, developer_id="dev_other")


def test_get_active_session_staleness_check(
    session_service: DeveloperSessionService,
) -> None:
    ses = session_service.start_session(developer_id="dev_tester")

    # When active and fresh
    active = session_service.get_active_session("dev_tester")
    assert active is not None
    assert active.session_id == ses.session_id

    # When aged beyond timeout
    old_time = datetime.now(UTC) - timedelta(minutes=30)
    session_service.session_repo.touch_heartbeat(ses.session_id, old_time)

    active_after = session_service.get_active_session("dev_tester")
    assert active_after is None

    # Database record is marked stale
    reloaded = session_service.session_repo.get_session(ses.session_id)
    assert reloaded is not None
    assert reloaded.status == SessionStatus.STALE.value


def test_get_session_history_pagination(
    session_service: DeveloperSessionService,
) -> None:
    # Create 5 sessions
    for i in range(5):
        ses = session_service.start_session(
            developer_id="dev_tester", project_path=f"/path/{i}"
        )
        session_service.end_session(ses.session_id, "dev_tester")

    # Page 1
    page1 = session_service.get_session_history(
        developer_id="dev_tester", limit=2, offset=0
    )
    assert page1.total_count == 5
    assert len(page1.sessions) == 2
    assert page1.limit == 2
    assert page1.offset == 0

    # Page 2
    page2 = session_service.get_session_history(
        developer_id="dev_tester", limit=2, offset=2
    )
    assert len(page2.sessions) == 2
    assert page2.sessions[0].session_id != page1.sessions[0].session_id

    # Page 3 (remainder)
    page3 = session_service.get_session_history(
        developer_id="dev_tester", limit=2, offset=4
    )
    assert len(page3.sessions) == 1


def test_cleanup_stale_sessions(
    session_service: DeveloperSessionService,
) -> None:
    ses1 = session_service.start_session(developer_id="dev_tester")
    ses2 = session_service.start_session(developer_id="dev_other")

    # Age ses1 beyond 15 mins
    old_time = datetime.now(UTC) - timedelta(minutes=25)
    session_service.session_repo.touch_heartbeat(ses1.session_id, old_time)

    cleaned_count = session_service.cleanup_stale_sessions(timeout_minutes=15)
    assert cleaned_count == 1

    reloaded1 = session_service.session_repo.get_session(ses1.session_id)
    assert reloaded1 is not None
    assert reloaded1.status == SessionStatus.STALE.value

    reloaded2 = session_service.session_repo.get_session(ses2.session_id)
    assert reloaded2 is not None
    assert reloaded2.status == SessionStatus.ACTIVE.value


def test_activity_recorder_session_integration(
    repos: tuple[
        InMemoryDeveloperRepository,
        InMemorySessionRepository,
        InMemoryActivityRepository,
    ],
    session_service: DeveloperSessionService,
) -> None:
    _, _, act_repo = repos
    recorder = ActivityRecorder(repository=act_repo, session_service=session_service)

    # Start active session
    active_session = session_service.start_session(developer_id="dev_tester")

    # 1. Activity without explicit session_id is automatically tagged with active session
    now = datetime.now(UTC)
    act1 = DeveloperActivity(
        event_id="evt_auto_1",
        developer_id="dev_tester",
        event_type="code_edit",
        timestamp=now,
        project_path="/proj/a",
    )
    recorded1 = recorder.record(act1)
    assert recorded1.session_id == active_session.session_id

    # 2. Activity with explicit session_id preserves provided session_id
    act2 = DeveloperActivity(
        event_id="evt_manual_2",
        developer_id="dev_tester",
        session_id="ses_custom_override",
        event_type="test_run",
        timestamp=now,
        project_path="/proj/a",
    )
    recorded2 = recorder.record(act2)
    assert recorded2.session_id == "ses_custom_override"

    # 3. Query activities by session
    session_acts = recorder.get_activities_for_session(active_session.session_id)
    assert len(session_acts) == 1
    assert session_acts[0].event_id == "evt_auto_1"


def test_session_service_validation_errors(
    session_service: DeveloperSessionService,
) -> None:
    # Invalid limit/offset
    with pytest.raises(ValueError, match="Limit must be a positive integer"):
        session_service.get_session_history("dev_tester", limit=0)
    with pytest.raises(ValueError, match="Offset cannot be negative"):
        session_service.get_session_history("dev_tester", offset=-1)

    # End session not found
    with pytest.raises(ValueError, match="Session not found"):
        session_service.end_session("ses_missing", "dev_tester")

    # End session invalid status
    ses = session_service.start_session(developer_id="dev_tester")
    with pytest.raises(ValueError, match="Invalid session terminal status"):
        session_service.end_session(
            ses.session_id, "dev_tester", status="invalid_status"
        )
