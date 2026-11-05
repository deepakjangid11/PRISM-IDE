import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from prism.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_api_developer_registration(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:6]
    payload = {
        "developer_id": f"dev_api_reg_{uid}",
        "name": "API Alice",
        "email": f"alice_{uid}@prism.io",
    }
    response = client.post("/developer/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["developer_id"] == f"dev_api_reg_{uid}"
    assert data["name"] == "API Alice"
    assert data["email"] == f"alice_{uid}@prism.io"

    # Duplicate registration returns 409
    dup_res = client.post("/developer/register", json=payload)
    assert dup_res.status_code == status.HTTP_409_CONFLICT


def test_api_developer_registration_validation(client: TestClient) -> None:
    # Invalid email
    response = client.post(
        "/developer/register",
        json={"name": "Bad", "email": "not-an-email"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_api_developer_registration_rejects_unsupported_fields(
    client: TestClient,
) -> None:
    # Extra fields (such as experience_level, primary_role) are forbidden by schema
    payload = {
        "name": "Deepak Jangid",
        "email": "deepak.phase16@prism.test",
        "experience_level": "intermediate",
        "primary_role": "AI Developer",
    }
    response = client.post("/developer/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    error_types = [err["type"] for err in data["detail"]]
    error_locs = [err["loc"][-1] for err in data["detail"]]
    assert "extra_forbidden" in error_types
    assert "experience_level" in error_locs
    assert "primary_role" in error_locs


def test_api_developer_registration_canonical_payload(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:6]
    payload = {
        "name": "Deepak Jangid",
        "email": f"deepak_{uid}@prism.test",
    }
    response = client.post("/developer/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["developer_id"].startswith("dev_")
    assert data["name"] == "Deepak Jangid"
    assert data["email"] == f"deepak_{uid}@prism.test"
    assert "created_at" in data
    assert "updated_at" in data


def test_api_developer_identification(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:6]
    dev_id = f"dev_api_ident_{uid}"
    email = f"ident_{uid}@prism.io"

    client.post(
        "/developer/register",
        json={
            "developer_id": dev_id,
            "name": "Ident Person",
            "email": email,
        },
    )

    # Lookup by ID
    res_id = client.post("/developer/identify", json={"developer_id": dev_id})
    assert res_id.status_code == status.HTTP_200_OK
    assert res_id.json()["developer_id"] == dev_id

    # Lookup by Email
    res_email = client.post("/developer/identify", json={"email": email})
    assert res_email.status_code == status.HTTP_200_OK
    assert res_email.json()["developer_id"] == dev_id

    # Non-existent
    res_404 = client.post(
        "/developer/identify", json={"developer_id": f"dev_unknown_{uid}"}
    )
    assert res_404.status_code == status.HTTP_404_NOT_FOUND


def test_api_developer_profile_crud(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:6]
    dev_id = f"dev_api_crud_{uid}"
    email = f"crud_{uid}@prism.io"

    client.post(
        "/developer/register",
        json={
            "developer_id": dev_id,
            "name": "Original Name",
            "email": email,
        },
    )

    # GET Profile
    get_res = client.get(f"/developer/{dev_id}/profile")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["name"] == "Original Name"

    # PUT Profile
    new_email = f"crud_new_{uid}@prism.io"
    put_res = client.put(
        f"/developer/{dev_id}/profile",
        json={"name": "Updated Name", "email": new_email},
    )
    assert put_res.status_code == status.HTTP_200_OK
    assert put_res.json()["name"] == "Updated Name"
    assert put_res.json()["email"] == new_email

    # GET Profile 404
    assert (
        client.get(f"/developer/dev_missing_{uid}/profile").status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_api_session_lifecycle(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:6]
    dev_id = f"dev_ses_api_{uid}"

    # Register developer first
    client.post(
        "/developer/register",
        json={"developer_id": dev_id, "name": "Session API Dev"},
    )

    # 1. Start session via /developer/session/start
    start_res = client.post(
        "/developer/session/start",
        json={"developer_id": dev_id, "project_path": "/repo/prism"},
    )
    assert start_res.status_code == status.HTTP_201_CREATED
    ses_data = start_res.json()
    session_id = ses_data["session_id"]
    assert ses_data["status"] == "active"

    # 2. GET Active session via /developer/session/active/{id}
    active_res = client.get(f"/developer/session/active/{dev_id}")
    assert active_res.status_code == status.HTTP_200_OK
    assert active_res.json()["session_id"] == session_id

    # 3. Heartbeat via /session/heartbeat (alias router)
    hb_res = client.post(
        "/session/heartbeat",
        json={
            "session_id": session_id,
            "developer_id": dev_id,
            "metadata": {"keystrokes": 50},
        },
    )
    assert hb_res.status_code == status.HTTP_200_OK
    assert hb_res.json()["metadata"]["keystrokes"] == 50

    # 4. End session via /developer/session/end
    end_res = client.post(
        "/developer/session/end",
        json={
            "session_id": session_id,
            "developer_id": dev_id,
            "status": "completed",
        },
    )
    assert end_res.status_code == status.HTTP_200_OK
    assert end_res.json()["status"] == "completed"

    # 5. GET Active session now returns 404
    assert (
        client.get(f"/session/active/{dev_id}").status_code == status.HTTP_404_NOT_FOUND
    )

    # 6. GET History via /session/history/{id}
    hist_res = client.get(f"/session/history/{dev_id}?limit=10&offset=0")
    assert hist_res.status_code == status.HTTP_200_OK
    hist_data = hist_res.json()
    assert hist_data["total_count"] >= 1
    assert hist_data["sessions"][0]["session_id"] == session_id


def test_api_session_error_handling(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:6]
    dev1 = f"dev_err_1_{uid}"
    dev2 = f"dev_err_2_{uid}"

    client.post(
        "/developer/register",
        json={"developer_id": dev1, "name": "Err Dev 1"},
    )
    client.post(
        "/developer/register",
        json={"developer_id": dev2, "name": "Err Dev 2"},
    )

    # Start session for dev 1
    start_res = client.post("/session/start", json={"developer_id": dev1})
    session_id = start_res.json()["session_id"]

    # Heartbeat with wrong developer ID returns 403 Forbidden
    forbidden_hb = client.post(
        "/session/heartbeat",
        json={"session_id": session_id, "developer_id": dev2},
    )
    assert forbidden_hb.status_code == status.HTTP_403_FORBIDDEN

    # End with wrong developer ID returns 403 Forbidden
    forbidden_end = client.post(
        "/session/end",
        json={"session_id": session_id, "developer_id": dev2},
    )
    assert forbidden_end.status_code == status.HTTP_403_FORBIDDEN

    # Non-existent session heartbeat returns 404
    res_404 = client.post(
        "/session/heartbeat",
        json={"session_id": f"ses_fake_{uid}", "developer_id": dev1},
    )
    assert res_404.status_code == status.HTTP_404_NOT_FOUND
