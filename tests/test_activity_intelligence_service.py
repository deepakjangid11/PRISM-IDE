import pytest

from prism.intelligence.activity_intelligence_service import (
    DeveloperActivityIntelligenceService,
)
from prism.intelligence.developer_session import DeveloperSessionService
from prism.intelligence.models.activity_classification_models import (
    ActivityIngestRequest,
    BatchActivityIngestRequest,
)
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemorySessionRepository,
)


@pytest.fixture
def service() -> DeveloperActivityIntelligenceService:
    dev_repo = InMemoryDeveloperRepository()
    session_repo = InMemorySessionRepository(dev_repo=dev_repo)
    act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    session_service = DeveloperSessionService(
        session_repo=session_repo, developer_repo=dev_repo
    )
    return DeveloperActivityIntelligenceService(
        activity_repo=act_repo,
        session_service=session_service,
    )


def test_ingest_activity_auto_session_association(
    service: DeveloperActivityIntelligenceService,
) -> None:
    # Set up active session for developer
    assert service.session_service is not None
    service.session_service.developer_repo.ensure_developer("dev_test_svc")
    session = service.session_service.start_session(
        "dev_test_svc", project_path="/prism"
    )

    req = ActivityIngestRequest(
        developer_id="dev_test_svc",
        event_type="file_edit",
        project_path="/prism",
        file_path="src/main.rs",
        code_snippet='fn main() { println!("hello"); }',
    )
    res = service.ingest_activity(req)

    assert res.developer_id == "dev_test_svc"
    assert res.session_id == session.session_id
    assert res.classification.language == "Rust"
    assert res.event_id.startswith("act_")


def test_ingest_activity_validates_required_fields(
    service: DeveloperActivityIntelligenceService,
) -> None:
    with pytest.raises(ValueError, match="developer_id cannot be empty"):
        service.ingest_activity(
            ActivityIngestRequest(
                developer_id="",
                event_type="edit",
                project_path="/p",
            )
        )

    with pytest.raises(ValueError, match="event_type cannot be empty"):
        service.ingest_activity(
            ActivityIngestRequest(
                developer_id="dev_1",
                event_type="",
                project_path="/p",
            )
        )


def test_ingest_activity_session_ownership_validation(
    service: DeveloperActivityIntelligenceService,
) -> None:
    assert service.session_service is not None
    service.session_service.developer_repo.ensure_developer("dev_owner_a")
    service.session_service.developer_repo.ensure_developer("dev_owner_b")
    session_other = service.session_service.start_session(
        "dev_owner_a", project_path="/p"
    )

    # Developer B attempts to use Developer A's session
    req = ActivityIngestRequest(
        developer_id="dev_owner_b",
        event_type="file_edit",
        project_path="/p",
        session_id=session_other.session_id,
    )
    with pytest.raises(
        ValueError, match="belongs to developer 'dev_owner_a', not 'dev_owner_b'"
    ):
        service.ingest_activity(req)


def test_batch_ingest_activities(
    service: DeveloperActivityIntelligenceService,
) -> None:
    batch = BatchActivityIngestRequest(
        activities=[
            ActivityIngestRequest(
                developer_id="dev_batch",
                event_type="file_create",
                project_path="/prism",
                file_path="src/index.ts",
                code_snippet="export const app = {};",
            ),
            ActivityIngestRequest(
                developer_id="dev_batch",
                event_type="test_run",
                project_path="/prism",
                file_path="tests/index.test.ts",
                code_snippet="test('works', () => {});",
            ),
        ]
    )
    res = service.batch_ingest(batch)
    assert len(res) == 2
    assert res[0].classification.language == "TypeScript"
    assert res[1].classification.category == "testing"


def test_get_history_and_session_activities(
    service: DeveloperActivityIntelligenceService,
) -> None:
    assert service.session_service is not None
    service.session_service.developer_repo.ensure_developer("dev_hist")
    ses = service.session_service.start_session("dev_hist", project_path="/prism")

    service.ingest_activity(
        ActivityIngestRequest(
            developer_id="dev_hist",
            event_type="file_edit",
            project_path="/prism",
            file_path="src/app.py",
            code_snippet="def foo(): pass",
            session_id=ses.session_id,
        )
    )

    history = service.get_history("dev_hist", limit=10, offset=0)
    assert history.total_count == 1
    assert len(history.activities) == 1
    assert history.activities[0].classification.language == "Python"

    session_acts = service.get_session_activities(ses.session_id)
    assert len(session_acts) == 1
    assert session_acts[0].session_id == ses.session_id
