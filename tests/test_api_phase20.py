"""API tests for Phase 20 endpoints (/llm/*, /rag/*, and streaming /mentoring/*)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from prism.api.dependencies import get_llm_service
from prism.api.main import app
from prism.llm.exceptions import (
    LLMAuthenticationError,
    LLMException,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)
from prism.llm.providers.mock_provider import MockLLMProvider


@pytest.fixture
def client() -> TestClient:
    # Ensure provider is mock for offline API testing
    llm = get_llm_service()
    mock_p = MockLLMProvider(
        default_response="Mock API LLM completion guidance.\n- Step 1: Follow design pattern.\n- Step 2: Test thoroughly."
    )
    mock_p.simulated_latency = 0.0
    llm.set_provider(mock_p)
    return TestClient(app)


def test_api_llm_health(client: TestClient) -> None:
    response = client.get("/llm/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["provider"] == "mock"


def test_api_llm_complete(client: TestClient) -> None:
    payload = {
        "messages": [
            {"role": "system", "content": "You are a test mentor."},
            {"role": "user", "content": "How do I write unit tests?"},
        ],
        "temperature": 0.2,
    }
    response = client.post("/llm/complete", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Mock API LLM completion guidance" in data["content"]
    assert data["provider"] == "mock"


def test_api_llm_complete_stream(client: TestClient) -> None:
    payload = {
        "messages": [
            {"role": "user", "content": "Stream me an explanation."},
        ],
    }
    response = client.post("/llm/complete/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "data:" in body
    assert "[DONE]" in body


def test_api_rag_lifecycle(client: TestClient, tmp_path: Path) -> None:
    # 1. Clear store
    clear_res = client.post("/rag/clear")
    assert clear_res.status_code == 200

    # 2. Index file with raw content
    index_res = client.post(
        "/rag/index/file",
        json={
            "file_path": "src/core/security.py",
            "content": "def hash_password(pwd: str) -> str:\n    return 'hashed_' + pwd\n",
        },
    )
    assert index_res.status_code == 200
    assert index_res.json()["chunks_indexed"] > 0

    # 3. Check stats
    stats_res = client.get("/rag/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["total_chunks"] > 0

    # 4. Search RAG
    search_res = client.post(
        "/rag/search",
        json={"query": "How is password hashing implemented?", "top_k": 2},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_retrieved"] > 0
    assert "hash_password" in search_data["chunks"][0]["chunk"]["content"]

    # 5. Index project directory
    (tmp_path / "app.py").write_text("def run(): pass\n", encoding="utf-8")
    proj_res = client.post(
        "/rag/index/project",
        json={"project_path": str(tmp_path)},
    )
    assert proj_res.status_code == 200
    assert proj_res.json()["total_chunks_indexed"] >= 1


def test_api_adaptive_mentoring_with_llm(client: TestClient) -> None:
    payload = {
        "developer_id": "dev_api_user",
        "query": "How do I handle background tasks in FastAPI?",
        "preferred_strategy": "guided_implementation",
        "use_llm": True,
        "enable_rag": True,
    }
    response = client.post("/mentoring/adaptive", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["developer_id"] == "dev_api_user"
    assert data["selected_strategy"] == "guided_implementation"
    assert "Mock API LLM completion guidance" in data["explanation"]
    assert data["provider_used"] == "mock"


def test_api_adaptive_mentoring_streaming(client: TestClient) -> None:
    payload = {
        "developer_id": "dev_api_user",
        "query": "Stream me instructions for microservices",
        "use_llm": True,
    }
    response = client.post("/mentoring/adaptive/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    text = response.text
    assert "data:" in text
    assert "[DONE]" in text


def test_api_rag_validation_errors(client: TestClient) -> None:
    # 1. Empty file_path
    res1 = client.post("/rag/index/file", json={"file_path": ""})
    assert res1.status_code == 422

    # 2. Non-existent project path
    res2 = client.post(
        "/rag/index/project",
        json={"project_path": "non/existent/path/for/sure_12345"},
    )
    assert res2.status_code == 404


def test_api_llm_health_failure(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    llm = get_llm_service()
    with patch.object(
        llm,
        "health_check",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Health down"),
    ):
        response = client.get("/llm/health")
        assert response.status_code == 500
        assert "Health down" in response.json()["detail"]


@pytest.mark.parametrize(
    ("exception_cls", "expected_status"),
    [
        (LLMAuthenticationError, 401),
        (LLMRateLimitError, 429),
        (LLMTimeoutError, 504),
        (LLMValidationError, 400),
        (LLMException, 502),
        (RuntimeError, 500),
    ],
)
def test_api_llm_complete_error_branches(
    client: TestClient,
    exception_cls: type[Exception],
    expected_status: int,
) -> None:
    from unittest.mock import AsyncMock, patch

    llm = get_llm_service()
    with patch.object(
        llm,
        "generate",
        new_callable=AsyncMock,
        side_effect=exception_cls("Simulated LLM error message"),
    ):
        req_payload = {
            "messages": [{"role": "user", "content": "Trigger failure"}],
        }
        response = client.post("/llm/complete", json=req_payload)
        assert response.status_code == expected_status


def test_api_llm_complete_stream_error(client: TestClient) -> None:
    from unittest.mock import patch

    llm = get_llm_service()

    async def failing_stream(req):
        raise LLMException("Stream broke mid-flight")
        yield  # make it a generator

    with patch.object(llm, "generate_stream", side_effect=failing_stream):
        req_payload = {
            "messages": [{"role": "user", "content": "Stream failure"}],
        }
        response = client.post("/llm/complete/stream", json=req_payload)
        assert response.status_code == 200
        text = response.text
        assert "Stream broke mid-flight" in text


def test_api_rag_error_handling(client: TestClient, tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch

    from prism.api.dependencies import get_rag_service

    rag = get_rag_service()

    # Index file: FileNotFoundError -> 404
    with patch.object(
        rag,
        "index_file",
        new_callable=AsyncMock,
        side_effect=FileNotFoundError("File missing on disk"),
    ):
        res = client.post("/rag/index/file", json={"file_path": "missing.py"})
        assert res.status_code == 404

    # Index file: generic Exception -> 500
    with patch.object(
        rag,
        "index_file",
        new_callable=AsyncMock,
        side_effect=OSError("Disk full error"),
    ):
        res = client.post("/rag/index/file", json={"file_path": "broken.py"})
        assert res.status_code == 500

    # Index project: FileNotFoundError -> 404
    valid_dir = tmp_path / "valid_dir"
    valid_dir.mkdir()
    with patch.object(
        rag,
        "index_project",
        new_callable=AsyncMock,
        side_effect=FileNotFoundError("Project folder went away"),
    ):
        res = client.post("/rag/index/project", json={"project_path": str(valid_dir)})
        assert res.status_code == 404

    # Index project: generic Exception -> 500
    with patch.object(
        rag,
        "index_project",
        new_callable=AsyncMock,
        side_effect=PermissionError("Permission denied"),
    ):
        res = client.post("/rag/index/project", json={"project_path": str(valid_dir)})
        assert res.status_code == 500

    # Search: generic Exception -> 500
    with patch.object(
        rag,
        "search",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Vector index corrupted"),
    ):
        res = client.post("/rag/search", json={"query": "test query"})
        assert res.status_code == 500
