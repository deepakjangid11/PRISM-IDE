
from fastapi.testclient import TestClient

from prism.api.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "application": "PRISM IDE",
    }


def test_analyze_project_endpoint(tmp_path) -> None:
    source_file = tmp_path / "example.py"
    source_file.write_text(
        "def hello():\n    pass\n",
        encoding="utf-8",
    )

    response = client.post(
        "/projects/analyze",
        json={"project_path": str(tmp_path)},
    )

    assert response.status_code == 200
    result = response.json()

    assert result["python_files_analyzed"] == 1
    assert result["files"][0]["functions"][0]["name"] == "hello"


def test_analyze_project_rejects_missing_path() -> None:
    response = client.post(
        "/projects/analyze",
        json={"project_path": "Z:/nonexistent/prism-project"},
    )

    assert response.status_code == 404
