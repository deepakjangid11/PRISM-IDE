"""Extended API tests for developer, mentoring, and intelligence error handling and edge cases."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from prism.api.dependencies import (
    adaptive_mentoring_engine,
    behavior_analyzer,
    identity_service,
    intelligence_engine,
    intelligence_orchestrator,
    mentoring_engine,
    session_service,
    skill_tracker,
)
from prism.api.main import app
from prism.exceptions.custom_exception import CustomException


def _make_custom_exception(msg: str) -> CustomException:
    try:
        raise RuntimeError(msg)
    except RuntimeError as err:
        return CustomException(err, sys)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# =========================================================================
# DEVELOPER ROUTE TESTS
# =========================================================================


def test_api_developer_behavior_errors(client: TestClient) -> None:
    analyzer = behavior_analyzer

    # 400 on ValueError
    with patch.object(
        analyzer, "analyze", side_effect=ValueError("Invalid activity sequence")
    ):
        res = client.post(
            "/developer/behavior",
            json={"developer_id": "dev_test", "activities": []},
        )
        assert res.status_code == 400
        assert "Invalid activity sequence" in res.json()["detail"]

    # 500 on CustomException
    with patch.object(
        analyzer,
        "analyze",
        side_effect=_make_custom_exception("Internal analysis crash"),
    ):
        res = client.post(
            "/developer/behavior",
            json={"developer_id": "dev_test", "activities": []},
        )
        assert res.status_code == 500


def test_api_developer_skills_record_errors(client: TestClient) -> None:
    tracker = skill_tracker
    evidence_payload = {
        "evidence_id": "ev_1",
        "developer_id": "dev_test",
        "skill_name": "python",
        "description": "Implemented unit tests for auth service",
        "timestamp": "2026-11-06T10:00:00Z",
    }

    # 400 on ValueError
    with patch.object(
        tracker, "record_evidence", side_effect=ValueError("Invalid confidence")
    ):
        res = client.post("/developer/skills/record", json=evidence_payload)
        assert res.status_code == 400

    # 500 on unexpected Exception
    with patch.object(
        tracker, "record_evidence", side_effect=RuntimeError("Storage crash")
    ):
        res = client.post("/developer/skills/record", json=evidence_payload)
        assert res.status_code == 500


def test_api_developer_skill_profile_error(client: TestClient) -> None:
    tracker = skill_tracker
    with patch.object(
        tracker, "get_profile", side_effect=ValueError("Malformed developer ID")
    ):
        res = client.get("/developer/skills/bad_id")
        assert res.status_code == 400


def test_api_developer_update_profile_branches(client: TestClient) -> None:
    identity_svc = identity_service
    update_payload = {"name": "Updated Name"}

    # 404 Not Found
    with patch.object(
        identity_svc, "update_profile", side_effect=ValueError("Developer not found")
    ):
        res = client.put("/developer/missing_dev/profile", json=update_payload)
        assert res.status_code == 404

    # 409 Conflict
    with patch.object(
        identity_svc,
        "update_profile",
        side_effect=ValueError("Email already registered"),
    ):
        res = client.put("/developer/dev_1/profile", json=update_payload)
        assert res.status_code == 409

    # 400 Bad Request
    with patch.object(
        identity_svc, "update_profile", side_effect=ValueError("Invalid role attribute")
    ):
        res = client.put("/developer/dev_1/profile", json=update_payload)
        assert res.status_code == 400


def test_api_developer_session_branches(client: TestClient) -> None:
    session_svc = session_service

    # 1. start_session 404 & 400
    with patch.object(
        session_svc, "start_session", side_effect=ValueError("Developer not found")
    ):
        res = client.post(
            "/developer/session/start",
            json={"developer_id": "ghost_dev", "project_path": "."},
        )
        assert res.status_code == 404

    with patch.object(
        session_svc, "start_session", side_effect=ValueError("Invalid parameters")
    ):
        res = client.post(
            "/developer/session/start",
            json={"developer_id": "dev_1", "project_path": "."},
        )
        assert res.status_code == 400

    # 2. session_heartbeat 404, 403, 409, 400
    hb_payload = {"session_id": "sess_1", "developer_id": "dev_1"}

    with patch.object(
        session_svc, "send_heartbeat", side_effect=ValueError("Session not found")
    ):
        res = client.post("/developer/session/heartbeat", json=hb_payload)
        assert res.status_code == 404

    with patch.object(
        session_svc,
        "send_heartbeat",
        side_effect=ValueError("Session does not belong to user"),
    ):
        res = client.post("/developer/session/heartbeat", json=hb_payload)
        assert res.status_code == 403

    with patch.object(
        session_svc,
        "send_heartbeat",
        side_effect=ValueError("Session expired and cannot heartbeat"),
    ):
        res = client.post("/developer/session/heartbeat", json=hb_payload)
        assert res.status_code == 409

    with patch.object(
        session_svc, "send_heartbeat", side_effect=ValueError("Bad request")
    ):
        res = client.post("/developer/session/heartbeat", json=hb_payload)
        assert res.status_code == 400

    # 3. end_session 404, 403, 400
    end_payload = {
        "session_id": "sess_1",
        "developer_id": "dev_1",
        "status": "completed",
    }

    with patch.object(
        session_svc, "end_session", side_effect=ValueError("Session not found")
    ):
        res = client.post("/developer/session/end", json=end_payload)
        assert res.status_code == 404

    with patch.object(
        session_svc, "end_session", side_effect=ValueError("Session does not belong")
    ):
        res = client.post("/developer/session/end", json=end_payload)
        assert res.status_code == 403

    with patch.object(
        session_svc, "end_session", side_effect=ValueError("Bad end request")
    ):
        res = client.post("/developer/session/end", json=end_payload)
        assert res.status_code == 400

    # 4. get_active_session 404
    with patch.object(session_svc, "get_active_session", return_value=None):
        res = client.get("/developer/session/active/ghost_dev")
        assert res.status_code == 404

    # 5. get_session_history 400
    with patch.object(
        session_svc,
        "get_session_history",
        side_effect=ValueError("Invalid history query"),
    ):
        res = client.get("/developer/session/history/bad_dev")
        assert res.status_code == 400


# =========================================================================
# MENTORING ROUTE TESTS
# =========================================================================


def test_api_mentoring_routes_error_handling(client: TestClient) -> None:
    # /mentoring/mentor ValueError -> 400, CustomException -> 500
    mentor_payload = {
        "developer_id": "dev_1",
        "mode": "learn",
        "query": "How do I use async?",
    }
    with patch.object(
        mentoring_engine, "mentor", side_effect=ValueError("Invalid mentoring query")
    ):
        res = client.post("/mentoring/request", json=mentor_payload)
        assert res.status_code == 400

    with patch.object(
        mentoring_engine,
        "mentor",
        side_effect=_make_custom_exception("Engine breakdown"),
    ):
        res = client.post("/mentoring/request", json=mentor_payload)
        assert res.status_code == 500

    # /mentoring/adaptive ValueError -> 400, Exception -> 500
    adaptive_payload = {
        "developer_id": "dev_1",
        "query": "Explain database indexes",
        "use_llm": False,
    }
    with patch.object(
        adaptive_mentoring_engine,
        "request_adaptive_mentoring_async",
        side_effect=ValueError("Query too short"),
    ):
        res = client.post("/mentoring/adaptive", json=adaptive_payload)
        assert res.status_code == 400

    with patch.object(
        adaptive_mentoring_engine,
        "request_adaptive_mentoring_async",
        side_effect=RuntimeError("Subsystem error"),
    ):
        res = client.post("/mentoring/adaptive", json=adaptive_payload)
        assert res.status_code == 500

    # /mentoring/history/{dev} -> 500
    with patch.object(
        adaptive_mentoring_engine,
        "get_session_history",
        side_effect=RuntimeError("DB query failure"),
    ):
        res = client.get("/mentoring/history/dev_1")
        assert res.status_code == 500

    # /mentoring/effectiveness/{dev} -> 500
    with patch.object(
        adaptive_mentoring_engine,
        "get_mentoring_effectiveness",
        side_effect=RuntimeError("Effectiveness calc failure"),
    ):
        res = client.get("/mentoring/effectiveness/dev_1")
        assert res.status_code == 500


# =========================================================================
# INTELLIGENCE ROUTE TESTS
# =========================================================================


def test_api_intelligence_routes_error_handling(client: TestClient) -> None:
    # /intelligence/profile/{id} -> 500
    with patch.object(
        intelligence_engine,
        "get_profile",
        side_effect=RuntimeError("Profile engine error"),
    ):
        res = client.get("/intelligence/profile/dev_test")
        assert res.status_code == 500

    # /intelligence/insights/{id} -> 500
    with patch.object(
        intelligence_engine,
        "get_insights",
        side_effect=RuntimeError("Insights engine error"),
    ):
        res = client.get("/intelligence/insights/dev_test")
        assert res.status_code == 500

    # /intelligence/trends/{id} -> 500
    with patch.object(
        intelligence_engine,
        "get_skill_trends",
        side_effect=RuntimeError("Trends engine error"),
    ):
        res = client.get("/intelligence/trends/dev_test")
        assert res.status_code == 500

    # /intelligence/refresh -> 500
    with patch.object(
        intelligence_engine,
        "analyze_developer",
        side_effect=RuntimeError("Analysis crash"),
    ):
        res = client.post("/intelligence/refresh", json={"developer_id": "dev_test"})
        assert res.status_code == 500

    # /intelligence/orchestrate/sync -> 500
    with patch.object(
        intelligence_orchestrator,
        "run_full_developer_sync",
        side_effect=RuntimeError("Sync error"),
    ):
        res = client.post(
            "/intelligence/orchestrate/sync", json={"developer_id": "dev_test"}
        )
        assert res.status_code == 500

    # /intelligence/orchestrate/activity -> 500
    activity_payload = {
        "event_id": "act_999",
        "developer_id": "dev_test",
        "event_type": "file_edit",
        "timestamp": "2026-11-06T10:00:00Z",
        "project_path": "/fake/path",
    }
    with patch.object(
        intelligence_orchestrator,
        "process_activity_and_recalibrate",
        side_effect=RuntimeError("Orchestration error"),
    ):
        res = client.post("/intelligence/orchestrate/activity", json=activity_payload)
        assert res.status_code == 500


def test_api_developer_identify_and_graph(client: TestClient) -> None:
    # 1. /developer/skills/graph
    res = client.get("/developer/skills/graph")
    assert res.status_code == 200
    assert "nodes" in res.json()

    # 2. /developer/identify ValueError -> 400
    with patch.object(
        identity_service,
        "identify_developer",
        side_effect=ValueError("Invalid identity parameters"),
    ):
        res = client.post("/developer/identify", json={"email": "bad@example.com"})
        assert res.status_code == 400


def test_api_mentoring_adaptive_stream_error(client: TestClient) -> None:
    async def failing_stream(req):
        raise RuntimeError("Adaptive streaming failure mid-transfer")
        yield  # make generator

    with patch.object(
        adaptive_mentoring_engine,
        "request_adaptive_mentoring_stream",
        side_effect=failing_stream,
    ):
        payload = {"developer_id": "dev_1", "query": "Stream break"}
        res = client.post("/mentoring/adaptive/stream", json=payload)
        assert res.status_code == 200
        assert "Adaptive streaming failure mid-transfer" in res.text
