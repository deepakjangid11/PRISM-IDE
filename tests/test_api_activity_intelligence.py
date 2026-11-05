import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from prism.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_api_record_activity(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:6]
    dev_id = f"dev_api_act_{uid}"

    # Register developer
    reg = client.post(
        "/developer/register", json={"developer_id": dev_id, "name": "Act Tester"}
    )
    assert reg.status_code == status.HTTP_201_CREATED

    payload = {
        "developer_id": dev_id,
        "event_type": "file_edit",
        "project_path": "C:/Projects/PRISM",
        "file_path": "src/services/billing.go",
        "code_snippet": 'package billing\nimport "fmt"\nfunc Process() {}',
    }
    res = client.post("/activity/record", json=payload)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()

    assert data["developer_id"] == dev_id
    assert data["classification"]["language"] == "Go"
    assert data["classification"]["category"] == "coding"
    assert "event_id" in data


def test_api_record_activity_validation(client: TestClient) -> None:
    # Empty developer_id -> 400
    res_empty = client.post(
        "/activity/record",
        json={"developer_id": "", "event_type": "edit", "project_path": "/p"},
    )
    assert res_empty.status_code == status.HTTP_400_BAD_REQUEST

    # Extra fields forbidden -> 422
    res_extra = client.post(
        "/activity/record",
        json={
            "developer_id": "dev_test",
            "event_type": "edit",
            "project_path": "/p",
            "unsupported_field": "disallowed",
        },
    )
    assert res_extra.status_code == 422


def test_api_batch_record_activities(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:6]
    dev_id = f"dev_api_batch_{uid}"
    client.post(
        "/developer/register", json={"developer_id": dev_id, "name": "Batch Tester"}
    )

    batch_payload = {
        "activities": [
            {
                "developer_id": dev_id,
                "event_type": "component_create",
                "project_path": "C:/Web",
                "file_path": "src/App.tsx",
                "code_snippet": "import React from 'react'; export const App = () => <div/>;",
            },
            {
                "developer_id": dev_id,
                "event_type": "test_failure",
                "project_path": "C:/Web",
                "file_path": "src/App.test.tsx",
                "code_snippet": "AssertionError: expected true",
            },
        ]
    }
    res = client.post("/activity/batch", json=batch_payload)
    assert res.status_code == status.HTTP_201_CREATED
    items = res.json()
    assert len(items) == 2
    assert items[0]["classification"]["language"] == "TypeScript"
    assert items[1]["classification"]["category"] == "testing"


def test_api_activity_history_and_analytics(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:6]
    dev_id = f"dev_api_analytics_{uid}"
    client.post(
        "/developer/register", json={"developer_id": dev_id, "name": "Analytics Dev"}
    )

    # Record two activities
    client.post(
        "/activity/record",
        json={
            "developer_id": dev_id,
            "event_type": "file_create",
            "project_path": "/proj",
            "file_path": "script.py",
            "code_snippet": "import pandas as pd\ndf = pd.DataFrame()",
        },
    )
    client.post(
        "/activity/record",
        json={
            "developer_id": dev_id,
            "event_type": "file_create",
            "project_path": "/proj",
            "file_path": "Main.java",
            "code_snippet": "public class Main { public static void main(String[] args) {} }",
        },
    )

    # 1. History
    hist = client.get(f"/activity/history/{dev_id}?limit=10&offset=0")
    assert hist.status_code == status.HTTP_200_OK
    hist_data = hist.json()
    assert hist_data["total_count"] == 2
    assert len(hist_data["activities"]) == 2

    # 2. Summary
    summ = client.get(f"/activity/summary/{dev_id}")
    assert summ.status_code == status.HTTP_200_OK
    summ_data = summ.json()
    assert summ_data["total_activities"] == 2

    # 3. Languages
    langs = client.get(f"/activity/languages/{dev_id}")
    assert langs.status_code == status.HTTP_200_OK
    lang_names = [l["language"] for l in langs.json()]
    assert "Python" in lang_names
    assert "Java" in lang_names
