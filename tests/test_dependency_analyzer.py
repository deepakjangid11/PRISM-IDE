
from pathlib import Path

from prism.intelligence.dependency_analyzer import (
    analyze_project_dependencies,
)


def test_analyze_project_dependencies(tmp_path: Path) -> None:
    package = tmp_path / "myapp"
    package.mkdir()

    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "utils.py").write_text(
        "def helper():\n    pass\n",
        encoding="utf-8",
    )
    (package / "main.py").write_text(
        "from myapp.utils import helper\nimport os\n",
        encoding="utf-8",
    )

    result = analyze_project_dependencies(tmp_path)

    assert result["total_python_files"] == 3
    assert result["local_dependencies"] >= 1
    assert result["external_dependencies"] >= 1

    local_dependencies = [
        item for item in result["dependencies"]
        if item["is_local"]
    ]

    assert any(
        item["target_file"] == "myapp/utils.py"
        for item in local_dependencies
    )


def test_analyze_project_dependencies_handles_empty_project(
    tmp_path: Path,
) -> None:
    result = analyze_project_dependencies(tmp_path)

    assert result["total_python_files"] == 0
    assert result["total_dependencies"] == 0


def test_analyze_project_dependencies_rejects_invalid_path(
    tmp_path: Path,
) -> None:
    invalid_path = tmp_path / "missing"

    try:
        analyze_project_dependencies(invalid_path)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for invalid project path")
