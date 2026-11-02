
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from prism.api.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_analyze_project_endpoint() -> None:
    project_path = Path(__file__).parent

    response = client.post(
        "/projects/analyze",
        json={"project_path": str(project_path)},
    )

    assert response.status_code == 200
    assert "files" in response.json()
    assert "python_files_analyzed" in response.json()


def test_analyze_project_rejects_missing_path() -> None:
    response = client.post(
        "/projects/analyze",
        json={"project_path": "nonexistent_project_directory"},
    )

    assert response.status_code == 404


def test_project_intelligence_endpoint() -> None:
    project_path = Path(__file__).parent

    expected_result = {
        "project_path": project_path.as_posix(),
        "project_context": {},
        "dependencies": {},
        "code_relationships": [],
        "summary": {
            "total_files": 3,
            "python_files_analyzed": 2,
            "total_classes": 1,
            "total_functions": 3,
            "total_function_calls": 2,
            "total_dependencies": 4,
            "local_dependencies": 2,
            "external_dependencies": 2,
        },
    }

    with patch(
        "prism.api.routes.project.build_project_intelligence"
    ) as mock_intelligence:
        mock_intelligence.return_value = expected_result

        response = client.post(
            "/projects/intelligence",
            json={"project_path": str(project_path)},
        )

    assert response.status_code == 200
    assert response.json() == expected_result
    mock_intelligence.assert_called_once()


def test_project_intelligence_rejects_missing_path() -> None:
    response = client.post(
        "/projects/intelligence",
        json={"project_path": "nonexistent_project_directory"},
    )

    assert response.status_code == 404
