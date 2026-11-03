from pathlib import Path

import pytest

from prism.intelligence.dependency_analyzer import (
    analyze_project_dependencies,
)
from prism.intelligence.models.dependency_models import (
    Dependency,
    FailedDependencyFile,
)


def test_analyze_project_dependencies(tmp_path: Path) -> None:
    package = tmp_path / "myapp"
    package.mkdir()

    (package / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )

    (package / "utils.py").write_text(
        "def helper():\n    pass\n",
        encoding="utf-8",
    )

    (package / "main.py").write_text(
        "from myapp.utils import helper\nimport os\n",
        encoding="utf-8",
    )

    result = analyze_project_dependencies(tmp_path)

    assert result.total_python_files == 3
    assert result.total_dependencies == 2
    assert result.local_dependencies == 1
    assert result.external_dependencies == 1

    assert len(result.dependencies) == 2

    local_dependency = next(
        dependency for dependency in result.dependencies if dependency.is_local
    )

    assert local_dependency.source_file == "myapp/main.py"
    assert local_dependency.imported_module == "myapp.utils"
    assert local_dependency.target_file == "myapp/utils.py"


def test_analyze_project_dependencies_handles_empty_project(
    tmp_path: Path,
) -> None:
    result = analyze_project_dependencies(tmp_path)

    assert result.total_python_files == 0
    assert result.total_dependencies == 0
    assert result.local_dependencies == 0
    assert result.external_dependencies == 0
    assert result.dependencies == []
    assert result.failed_files == []


def test_analyze_project_dependencies_rejects_invalid_path(
    tmp_path: Path,
) -> None:
    invalid_path = tmp_path / "does_not_exist"

    with pytest.raises(ValueError, match="Invalid project directory"):
        analyze_project_dependencies(invalid_path)


def test_analyze_project_dependencies_handles_failed_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "valid.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def broken(:", encoding="utf-8")

    result = analyze_project_dependencies(tmp_path)

    assert result.total_python_files == 2
    assert len(result.failed_files) == 1
    failed_file = result.failed_files[0]
    assert isinstance(failed_file, FailedDependencyFile)
    assert failed_file.file_path == "broken.py"
    assert "syntax" in failed_file.error.lower()

    assert len(result.dependencies) == 1
    assert isinstance(result.dependencies[0], Dependency)
    assert result.dependencies[0].imported_module == "os"
