from prism.intelligence.models.dependency_models import (
    Dependency,
    DependencyAnalysis,
    FailedDependencyFile,
)


def test_dependency_model() -> None:
    dependency = Dependency(
        source_file="src/prism/api/main.py",
        imported_module="prism.config.settings",
        target_file="src/prism/config/settings.py",
        is_local=True,
        line=10,
    )

    assert dependency.source_file == "src/prism/api/main.py"
    assert dependency.imported_module == "prism.config.settings"
    assert dependency.target_file == "src/prism/config/settings.py"
    assert dependency.is_local is True
    assert dependency.line == 10


def test_failed_dependency_file_model() -> None:
    failed_file = FailedDependencyFile(
        file_path="src/prism/example.py",
        error="Invalid Python syntax",
    )

    assert failed_file.file_path == "src/prism/example.py"
    assert failed_file.error == "Invalid Python syntax"


def test_dependency_analysis_model() -> None:
    analysis = DependencyAnalysis(
        project_path="C:/Users/HP/Downloads/PRISM IDE",
        total_python_files=10,
        total_dependencies=8,
        local_dependencies=5,
        external_dependencies=3,
        dependencies=[],
        failed_files=[],
    )

    assert analysis.total_python_files == 10
    assert analysis.total_dependencies == 8
    assert analysis.local_dependencies == 5
    assert analysis.external_dependencies == 3
    assert analysis.dependencies == []
    assert analysis.failed_files == []
