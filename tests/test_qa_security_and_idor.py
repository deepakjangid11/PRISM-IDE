"""Comprehensive QA Security and IDOR Protection Tests.

Validates:
1. Multi-account registration and authentication.
2. Token lifecycle and revocation on logout.
3. Cross-account access control (IDOR prevention) across tasks, evaluations,
   progress, mentoring conversations, skills, and reports.
4. Administrative role privilege override.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from prism.api.main import app

client = TestClient(app)


def _register_and_login(role: str = "developer") -> tuple[str, str, str]:
    """Helper to register and login a test developer, returning (dev_id, email, token)."""
    uid = uuid.uuid4().hex[:8]
    dev_id = f"dev_{uid}"
    email = f"user_{uid}@prism-test.org"
    password = "SecurePassword123!"

    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "name": f"User {uid}",
            "developer_id": dev_id,
            "role": role,
        },
    )
    assert reg.status_code == 201, f"Registration failed: {reg.text}"
    token = reg.json()["access_token"]
    return dev_id, email, token


def test_token_revocation_on_logout() -> None:
    """Verify that logging out revokes the access token and subsequent use is denied."""
    dev_id, _, token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works before logout
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["developer_id"] == dev_id

    # Call logout
    logout_resp = client.post("/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "logged_out"

    # Token must now be rejected
    rejected_resp = client.get("/auth/me", headers=headers)
    assert rejected_resp.status_code == 401
    assert "revoked" in rejected_resp.json()["detail"].lower()


def test_cross_account_task_idor_protection() -> None:
    """Verify that Developer A cannot access, submit, or evaluate Developer B's tasks."""
    dev_a_id, _, token_a = _register_and_login()
    dev_b_id, _, token_b = _register_and_login()

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Generate a task for Developer B
    gen_resp = client.post(
        "/tasks/generate",
        json={"developer_id": dev_b_id, "target_goal": "Python", "limit": 1},
        headers=headers_b,
    )
    assert gen_resp.status_code == 200
    tasks = gen_resp.json()
    assert len(tasks) > 0
    task_b_id = tasks[0]["task_id"]

    # 1. Developer A attempts to read Developer B's task list -> 403 Forbidden
    cross_list = client.get(f"/tasks/developer/{dev_b_id}", headers=headers_a)
    assert cross_list.status_code == 403
    assert "forbidden" in cross_list.json()["detail"].lower()

    # 2. Developer B can read their own task list -> 200 OK
    own_list = client.get(f"/tasks/developer/{dev_b_id}", headers=headers_b)
    assert own_list.status_code == 200

    # 3. Developer A attempts to inspect Developer B's specific task -> 403 Forbidden
    cross_task = client.get(f"/tasks/{task_b_id}", headers=headers_a)
    assert cross_task.status_code == 403

    # 4. Developer A attempts to submit Developer B's task -> 403 Forbidden
    cross_submit = client.post(
        f"/tasks/{task_b_id}/submit",
        json={"source_code": "print('exploit')", "developer_id": dev_a_id},
        headers=headers_a,
    )
    assert cross_submit.status_code == 403

    # 5. Developer A attempts to evaluate Developer B's task -> 403 Forbidden
    cross_eval = client.post(
        f"/tasks/{task_b_id}/evaluate",
        json={"developer_id": dev_a_id, "passed": True, "score": 1.0},
        headers=headers_a,
    )
    assert cross_eval.status_code == 403


def test_cross_account_evaluations_and_progress_idor() -> None:
    """Verify Developer A cannot view Developer B's evaluations or progress dashboard."""
    _dev_a_id, _, token_a = _register_and_login()
    dev_b_id, _, token_b = _register_and_login()

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Developer A attempts to read Developer B's evaluation records -> 403
    eval_resp = client.get(f"/evaluation/developer/{dev_b_id}", headers=headers_a)
    assert eval_resp.status_code == 403

    # Developer B reading their own evaluation records -> 200
    b_eval_resp = client.get(f"/evaluation/developer/{dev_b_id}", headers=headers_b)
    assert b_eval_resp.status_code == 200

    # Progress endpoints: Dev A accessing Dev B's progress -> 403 Forbidden
    assert (
        client.get(f"/progress/{dev_b_id}/dashboard", headers=headers_a).status_code
        == 403
    )
    assert (
        client.get(f"/progress/{dev_b_id}/skills", headers=headers_a).status_code == 403
    )
    assert (
        client.get(f"/progress/{dev_b_id}/history", headers=headers_a).status_code
        == 403
    )
    assert (
        client.get(
            f"/progress/{dev_b_id}/learning-paths", headers=headers_a
        ).status_code
        == 403
    )

    # Dev B accessing own progress -> 200
    assert (
        client.get(f"/progress/{dev_b_id}/dashboard", headers=headers_b).status_code
        == 200
    )


def test_cross_account_mentoring_conversations_idor() -> None:
    """Verify Developer A cannot read or post to Developer B's mentoring conversations."""
    _dev_a_id, _, token_a = _register_and_login()
    dev_b_id, _, token_b = _register_and_login()

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Start a conversation for Dev B
    start_resp = client.post(
        "/mentoring/conversations/start",
        json={
            "developer_id": dev_b_id,
            "initial_query": "How does async/await work in Python?",
        },
        headers=headers_b,
    )
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    conv_id = start_data["conversation"]["conversation_id"]

    # Developer A attempts to read Developer B's conversation -> 403
    cross_conv = client.get(f"/mentoring/conversations/{conv_id}", headers=headers_a)
    assert cross_conv.status_code == 403

    # Developer A attempts to send message to Dev B's conversation -> 403
    cross_msg = client.post(
        f"/mentoring/conversations/{conv_id}/message",
        json={"message": "Malicious payload"},
        headers=headers_a,
    )
    assert cross_msg.status_code == 403

    # Developer A attempts to request hint on Dev B's conversation -> 403
    cross_hint = client.post(
        f"/mentoring/conversations/{conv_id}/hint",
        headers=headers_a,
    )
    assert cross_hint.status_code == 403

    # Developer A attempts to list Dev B's conversations -> 403
    cross_list = client.get(
        f"/mentoring/conversations/developer/{dev_b_id}", headers=headers_a
    )
    assert cross_list.status_code == 403

    # Developer B reading own conversation -> 200
    own_conv = client.get(f"/mentoring/conversations/{conv_id}", headers=headers_b)
    assert own_conv.status_code == 200


def test_cross_account_skills_and_reports_idor() -> None:
    """Verify Developer A cannot view or manipulate Developer B's skills, gaps, or reports."""
    _dev_a_id, _, token_a = _register_and_login()
    dev_b_id, _, token_b = _register_and_login()

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Skills endpoints: Dev A accessing Dev B's skill data -> 403
    assert (
        client.get(f"/skills/profile/{dev_b_id}", headers=headers_a).status_code == 403
    )
    assert (
        client.get(f"/skills/evidence/{dev_b_id}", headers=headers_a).status_code == 403
    )
    assert (
        client.get(f"/skills/proficiency/{dev_b_id}", headers=headers_a).status_code
        == 403
    )
    assert client.get(f"/skills/gaps/{dev_b_id}", headers=headers_a).status_code == 403
    assert (
        client.get(f"/skills/recommendations/{dev_b_id}", headers=headers_a).status_code
        == 403
    )
    assert (
        client.get(
            f"/skills/learning-path/{dev_b_id}?target_goal=Python", headers=headers_a
        ).status_code
        == 403
    )

    # Reports endpoints: Dev A accessing Dev B's reports -> 403
    assert (
        client.get(f"/reports/developer/{dev_b_id}", headers=headers_a).status_code
        == 403
    )
    assert (
        client.post(
            "/reports/generate",
            json={"developer_id": dev_b_id, "report_type": "comprehensive"},
            headers=headers_a,
        ).status_code
        == 403
    )

    # Dev B accessing own skill data -> 200
    assert (
        client.get(f"/skills/profile/{dev_b_id}", headers=headers_b).status_code == 200
    )


def test_admin_role_privilege_override() -> None:
    """Verify an admin user can access resources across developers."""
    _, _, token_admin = _register_and_login(role="admin")
    dev_b_id, _, _ = _register_and_login(role="developer")

    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # Admin accessing Dev B's progress dashboard -> 200 OK
    dash_resp = client.get(f"/progress/{dev_b_id}/dashboard", headers=headers_admin)
    assert dash_resp.status_code == 200

    # Admin accessing Dev B's skills profile -> 200 OK
    profile_resp = client.get(f"/skills/profile/{dev_b_id}", headers=headers_admin)
    assert profile_resp.status_code == 200
