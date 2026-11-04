from datetime import UTC, datetime

from fastapi.testclient import TestClient

from prism.api.main import app

client = TestClient(app)


def test_api_developer_behavior_endpoint() -> None:
    now = datetime.now(UTC).isoformat()
    response = client.post(
        "/developer/behavior",
        json={
            "activities": [
                {
                    "event_id": "e1",
                    "developer_id": "api_dev",
                    "event_type": "code_edit",
                    "timestamp": now,
                    "project_path": "/app",
                },
                {
                    "event_id": "e2",
                    "developer_id": "api_dev",
                    "event_type": "file_save",
                    "timestamp": now,
                    "project_path": "/app",
                },
            ],
            "developer_id": "api_dev",
            "project_path": "/app",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["developer_id"] == "api_dev"
    assert data["total_events"] == 2


def test_api_developer_behavior_mismatch_error() -> None:
    now = datetime.now(UTC).isoformat()
    response = client.post(
        "/developer/behavior",
        json={
            "activities": [
                {
                    "event_id": "e1",
                    "developer_id": "devA",
                    "event_type": "code_edit",
                    "timestamp": now,
                    "project_path": "/app",
                },
                {
                    "event_id": "e2",
                    "developer_id": "devB",
                    "event_type": "code_edit",
                    "timestamp": now,
                    "project_path": "/app",
                },
            ],
        },
    )
    assert response.status_code == 400
    assert "same developer and project" in response.json()["detail"]


def test_api_skills_record_and_get() -> None:
    now = datetime.now(UTC).isoformat()
    # Record evidence
    ev_response = client.post(
        "/developer/skills/record",
        json={
            "evidence_id": "ev-api-1",
            "developer_id": "api_skill_dev",
            "skill_name": "Python",
            "evidence_type": "code_artifact",
            "description": "Implemented fast sorting algorithm",
            "timestamp": now,
            "project_path": "/workspace",
        },
    )
    assert ev_response.status_code == 200
    assert ev_response.json()["skill_name"] == "Python"

    # Get profile
    prof_response = client.get("/developer/skills/api_skill_dev")
    assert prof_response.status_code == 200
    prof_data = prof_response.json()
    assert prof_data["developer_id"] == "api_skill_dev"
    assert "python" in prof_data["skills"]


def test_api_get_skill_graph() -> None:
    response = client.get("/developer/skills/graph")
    assert response.status_code == 200
    data = response.json()
    assert "Python" in data["skills"]
    assert len(data["relationships"]) > 0


def test_api_learning_endpoints() -> None:
    # 1. Gaps
    gap_resp = client.post(
        "/learning/gaps",
        json={
            "developer_id": "api_learner",
            "target_skill": "Machine Learning",
        },
    )
    assert gap_resp.status_code == 200
    gaps = gap_resp.json()
    assert len(gaps) > 0
    missing_skills = [g["missing_skill"] for g in gaps]
    assert "Python" in missing_skills

    # 2. Paths
    path_resp = client.post(
        "/learning/paths",
        json={
            "developer_id": "api_learner",
            "target_goal": "Machine Learning",
        },
    )
    assert path_resp.status_code == 200
    path_data = path_resp.json()
    assert "Python" in path_data["steps"]

    # 3. Recommendations
    rec_resp = client.post(
        "/learning/recommendations",
        json={
            "developer_id": "api_learner",
            "target_skill": "Machine Learning",
        },
    )
    assert rec_resp.status_code == 200
    assert len(rec_resp.json()) > 0


def test_api_mentoring_endpoints() -> None:
    # Build Mode request
    build_resp = client.post(
        "/mentoring/request",
        json={
            "developer_id": "api_dev",
            "mode": "build",
            "query": "How do I optimize code relationships?",
        },
    )
    assert build_resp.status_code == 200
    build_data = build_resp.json()
    assert build_data["mode"] == "build"
    assert len(build_data["actionable_next_steps"]) > 0

    # Learn Mode request
    learn_resp = client.post(
        "/mentoring/request",
        json={
            "developer_id": "api_dev",
            "mode": "learn",
            "query": "Teach me Machine Learning",
            "target_skill": "Machine Learning",
        },
    )
    assert learn_resp.status_code == 200
    learn_data = learn_resp.json()
    assert learn_data["mode"] == "learn"
    assert len(learn_data["recommendations"]) > 0

    # Validation failure: missing query
    invalid_resp = client.post(
        "/mentoring/request",
        json={
            "developer_id": "api_dev",
            "mode": "build",
            "query": "   ",
        },
    )
    assert invalid_resp.status_code == 400
