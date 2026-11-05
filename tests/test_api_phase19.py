"""Comprehensive API integration tests for Phase 19 endpoints."""

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from prism.api.dependencies import developer_repo
from prism.api.main import app

client = TestClient(app)


def _create_test_developer() -> str:
    dev_id = f"dev_api19_{uuid.uuid4().hex[:8]}"
    developer_repo.create_developer(
        dev_id, name="API Tester", email=f"{dev_id}@prism.dev"
    )
    return dev_id


def test_api_intelligence_profile_and_refresh():
    dev_id = _create_test_developer()

    # GET profile
    res = client.get(f"/intelligence/profile/{dev_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["developer_id"] == dev_id
    assert "overall_status" in data

    # POST refresh
    res_refresh = client.post("/intelligence/refresh", json={"developer_id": dev_id})
    assert res_refresh.status_code == 200
    ref_data = res_refresh.json()
    assert ref_data["developer_id"] == dev_id

    # GET insights & trends
    res_insights = client.get(f"/intelligence/insights/{dev_id}")
    assert res_insights.status_code == 200
    assert isinstance(res_insights.json(), list)

    res_trends = client.get(f"/intelligence/trends/{dev_id}")
    assert res_trends.status_code == 200
    assert isinstance(res_trends.json(), list)


def test_api_tasks_lifecycle():
    dev_id = _create_test_developer()

    # POST /tasks/generate
    gen_res = client.post(
        "/tasks/generate",
        json={"developer_id": dev_id, "target_role": "backend_developer", "limit": 2},
    )
    assert gen_res.status_code == 200
    tasks = gen_res.json()
    assert len(tasks) > 0
    task_id = tasks[0]["task_id"]

    # GET /tasks/{task_id}
    get_res = client.get(f"/tasks/{task_id}")
    assert get_res.status_code == 200
    assert get_res.json()["task_id"] == task_id

    # GET /tasks/recommendations/{developer_id}
    rec_res = client.get(f"/tasks/recommendations/{dev_id}?limit=2")
    assert rec_res.status_code == 200
    assert len(rec_res.json()) > 0

    # PATCH /tasks/{task_id}/status
    patch_res = client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "in_progress", "notes": "Started implementing endpoints"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "in_progress"

    # POST /tasks/{task_id}/evaluate
    eval_res = client.post(
        f"/tasks/{task_id}/evaluate",
        json={
            "developer_id": dev_id,
            "passed": True,
            "score": 0.9,
            "execution_notes": "Implemented with 100% tests passing",
            "verified_artifacts": ["src/service.py"],
        },
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["passed"] is True
    assert eval_data["generated_evidence_id"] is not None


def test_api_adaptive_mentoring():
    dev_id = _create_test_developer()

    # POST /mentoring/adaptive
    mentor_res = client.post(
        "/mentoring/adaptive",
        json={
            "developer_id": dev_id,
            "query": "How do I fix unexpected database connection timeout in MySQL?",
        },
    )
    assert mentor_res.status_code == 200
    m_data = mentor_res.json()
    assert m_data["developer_id"] == dev_id
    assert m_data["selected_strategy"] == "debugging_guidance"

    # GET /mentoring/history/{developer_id}
    hist_res = client.get(f"/mentoring/history/{dev_id}")
    assert hist_res.status_code == 200
    assert len(hist_res.json()) >= 1

    # GET /mentoring/effectiveness/{developer_id}
    eff_res = client.get(f"/mentoring/effectiveness/{dev_id}")
    assert eff_res.status_code == 200
    assert eff_res.json()["total_sessions"] >= 1


def test_api_analytics_endpoints():
    dev_id = _create_test_developer()

    # GET /analytics/performance/{developer_id}
    perf_res = client.get(f"/analytics/performance/{dev_id}")
    assert perf_res.status_code == 200
    assert perf_res.json()["developer_id"] == dev_id

    # GET /analytics/improvement/{developer_id}
    imp_res = client.get(f"/analytics/improvement/{dev_id}")
    assert imp_res.status_code == 200

    # GET /analytics/learning/{developer_id}
    lrn_res = client.get(f"/analytics/learning/{dev_id}")
    assert lrn_res.status_code == 200

    # GET /analytics/history/{developer_id}
    hist_res = client.get(f"/analytics/history/{dev_id}")
    assert hist_res.status_code == 200
    assert isinstance(hist_res.json(), list)


def test_api_feedback_endpoints():
    dev_id = _create_test_developer()

    # GET /feedback/{developer_id}
    fb_res = client.get(f"/feedback/{dev_id}")
    assert fb_res.status_code == 200
    assert len(fb_res.json()) >= 1

    # POST /feedback/generate
    gen_fb = client.post("/feedback/generate", json={"developer_id": dev_id})
    assert gen_fb.status_code == 200
    assert len(gen_fb.json()) >= 1

    # GET /feedback/history/{developer_id}
    hist_fb = client.get(f"/feedback/history/{dev_id}")
    assert hist_fb.status_code == 200
    assert len(hist_fb.json()) >= 1


def test_api_adaptation_endpoints():
    dev_id = _create_test_developer()

    # POST /adaptation/adapt
    adapt_res = client.post("/adaptation/adapt", json={"developer_id": dev_id})
    assert adapt_res.status_code == 200
    assert adapt_res.json()["new_strategy"] in [
        "standard",
        "remediation",
        "practice_intensive",
        "accelerated",
        "prerequisite_first",
    ]

    # GET /adaptation/strategy/{developer_id}
    strat_res = client.get(f"/adaptation/strategy/{dev_id}")
    assert strat_res.status_code == 200
    assert "new_strategy" in strat_res.json()

    # GET /adaptation/history/{developer_id}
    hist_adapt = client.get(f"/adaptation/history/{dev_id}")
    assert hist_adapt.status_code == 200
    assert len(hist_adapt.json()) >= 1


def test_api_orchestration_endpoints():
    dev_id = _create_test_developer()
    now = datetime.now(UTC)

    # POST /intelligence/orchestrate/activity
    act_payload = {
        "event_id": f"evt_{uuid.uuid4().hex[:8]}",
        "developer_id": dev_id,
        "event_type": "git_commit",
        "timestamp": now.isoformat(),
        "project_path": "/prism",
        "file_path": "/prism/api.py",
        "metadata": {"language": "python"},
    }
    orch_res = client.post("/intelligence/orchestrate/activity", json=act_payload)
    assert orch_res.status_code == 200
    assert orch_res.json()["status"] == "success"

    # POST /intelligence/orchestrate/sync
    sync_res = client.post(
        "/intelligence/orchestrate/sync",
        json={"developer_id": dev_id, "target_role": "backend_developer"},
    )
    assert sync_res.status_code == 200
    assert sync_res.json()["status"] == "synced"


def test_api_error_branches_and_edge_cases():
    # 404 for non-existent tasks
    get_task_res = client.get("/tasks/non_existent_task_123")
    assert get_task_res.status_code == 404

    patch_task_res = client.patch(
        "/tasks/non_existent_task_123/status",
        json={"status": "in_progress", "notes": "Working on it"},
    )
    assert patch_task_res.status_code == 404

    eval_task_res = client.post(
        "/tasks/non_existent_task_123/evaluate",
        json={
            "developer_id": "any_dev",
            "passed": True,
            "score": 0.9,
            "execution_notes": "Done",
            "verified_artifacts": [],
        },
    )
    assert eval_task_res.status_code == 404

    # 200 with empty list for non-existent developer in recommendations
    recs_res = client.get("/tasks/recommendations/non_existent_developer_123")
    assert recs_res.status_code == 200
    assert recs_res.json() == []

    # 200 with empty list for non-existent developer in tasks generate
    gen_res = client.post(
        "/tasks/generate",
        json={"developer_id": "non_existent_developer_123"},
    )
    assert gen_res.status_code == 200
    assert gen_res.json() == []

    # Initial baseline profile for newly queried developer
    prof_res = client.get("/intelligence/profile/non_existent_dev")
    assert prof_res.status_code == 200
    assert prof_res.json()["developer_id"] == "non_existent_dev"
    assert prof_res.json()["has_sufficient_data"] is False

    # Insights and trends for newly queried developer
    assert client.get("/intelligence/insights/non_existent_dev").status_code == 200
    assert client.get("/intelligence/trends/non_existent_dev").status_code == 200

    # Analytics for newly queried developer
    perf_res = client.get("/analytics/performance/non_existent_dev")
    assert perf_res.status_code == 200
    assert perf_res.json()["developer_id"] == "non_existent_dev"
    assert client.get("/analytics/improvement/non_existent_dev").status_code == 200
    assert client.get("/analytics/learning/non_existent_dev").status_code == 200

    # 400 for empty query in adaptive mentoring
    mentor_res = client.post(
        "/mentoring/adaptive",
        json={"developer_id": "any_dev", "query": ""},
    )
    assert mentor_res.status_code == 400
