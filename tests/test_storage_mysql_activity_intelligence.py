import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from prism.config.settings import settings
from prism.intelligence.activity_intelligence_service import (
    DeveloperActivityIntelligenceService,
)
from prism.intelligence.developer_session import DeveloperSessionService
from prism.intelligence.models.activity_classification_models import (
    ActivityIngestRequest,
)
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
from prism.storage.repositories.mysql_session_repo import MySQLSessionRepository


def is_mysql_test_server_live() -> bool:
    try:
        engine = create_engine(settings.test_database_url, pool_pre_ping=True)
        return check_db_connection(engine)
    except SQLAlchemyError, OSError:
        return False


pytestmark = pytest.mark.skipif(
    not is_mysql_test_server_live(),
    reason="Live MySQL test database 'prism_test_db' is not reachable.",
)


@pytest.fixture
def session_factory() -> Generator[sessionmaker]:
    engine = create_engine(
        settings.test_database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    create_schema_for_test(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    yield factory

    drop_schema_for_test(engine)
    engine.dispose()


def test_mysql_activity_intelligence_persistence_and_filtering(
    session_factory: sessionmaker,
) -> None:
    dev_repo = MySQLDeveloperRepository(session_factory)
    ses_repo = MySQLSessionRepository(session_factory, developer_repo=dev_repo)
    act_repo = MySQLActivityRepository(session_factory, developer_repo=dev_repo)
    session_service = DeveloperSessionService(
        session_repo=ses_repo, developer_repo=dev_repo
    )

    service = DeveloperActivityIntelligenceService(
        activity_repo=act_repo,
        session_service=session_service,
    )

    uid = uuid.uuid4().hex[:6]
    dev_id = f"dev_mysql_act_{uid}"
    dev_repo.create_developer(dev_id, name="MySQL Act Tester")

    # Start active session
    session = session_service.start_session(dev_id, project_path="/test/prism")

    # 1. Ingest Go activity
    res_go = service.ingest_activity(
        ActivityIngestRequest(
            developer_id=dev_id,
            event_type="file_edit",
            project_path="/test/prism",
            file_path="server/main.go",
            code_snippet="func main() { go worker(); }",
        )
    )
    assert res_go.session_id == session.session_id
    assert res_go.classification.language == "Go"
    assert res_go.classification.concept == "Concurrency"

    # 2. Ingest Python activity
    res_py = service.ingest_activity(
        ActivityIngestRequest(
            developer_id=dev_id,
            event_type="test_run",
            project_path="/test/prism",
            file_path="tests/test_server.py",
            code_snippet="def test_worker(): assert True",
        )
    )
    assert res_py.classification.language == "Python"
    assert res_py.classification.category == "testing"

    # 3. Query filtered history
    history_all = service.get_history(dev_id)
    assert history_all.total_count == 2

    history_go = service.get_history(dev_id, language="Go")
    assert history_go.total_count == 1
    assert history_go.activities[0].classification.language == "Go"

    history_testing = service.get_history(dev_id, category="testing")
    assert history_testing.total_count == 1
    assert history_testing.activities[0].classification.category == "testing"

    # 4. Summary & Languages
    summary = service.get_activity_summary(dev_id)
    assert summary.total_activities == 2
    assert summary.testing_frequency == 0.5

    langs = service.get_language_distribution(dev_id)
    lang_map = {l.language: l.count for l in langs}
    assert lang_map["Go"] == 1
    assert lang_map["Python"] == 1
