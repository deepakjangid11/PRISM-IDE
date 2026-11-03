from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from prism.api.main import app
from prism.intelligence.models.dependency_models import (
    Dependency,
    DependencyAnalysis,
)
from prism.intelligence.models.project_intelligence_models import (
    ContextClass,
    ContextFailedFile,
    ContextFile,
    ContextFunction,
    ContextMethod,
    ProjectContext,
    ProjectIntelligence,
    ProjectIntelligenceSummary,
)
from prism.intelligence.models.relationship_models import (
    ClassRelationship,
    CodeRelationshipAnalysis,
    FunctionCall,
    FunctionRelationship,
)
from prism.intelligence.project_intelligence import (
    build_project_intelligence,
)


def test_context_models_construction() -> None:
    method = ContextMethod(name="do_work", line=5, is_async=True)
    assert method.name == "do_work"
    assert method.line == 5
    assert method.is_async is True
    assert method["name"] == "do_work"

    cls = ContextClass(name="Worker", line=4, methods=[method])
    assert cls.name == "Worker"
    assert cls.line == 4
    assert len(cls.methods) == 1
    assert cls["methods"][0]["name"] == "do_work"

    func = ContextFunction(name="helper", line=15, is_async=False)
    assert func.name == "helper"
    assert func.line == 15
    assert func.is_async is False

    context_file = ContextFile(
        file_path="src/worker.py",
        classes=[cls],
        functions=[func],
        imports=["os", "sys"],
    )
    assert context_file.file_path == "src/worker.py"
    assert len(context_file.classes) == 1
    assert len(context_file.functions) == 1
    assert context_file.imports == ["os", "sys"]

    failed_file = ContextFailedFile(
        file_path="src/broken.py",
        error="SyntaxError: invalid syntax",
    )
    assert failed_file.file_path == "src/broken.py"
    assert failed_file.error == "SyntaxError: invalid syntax"

    project_context = ProjectContext(
        project_path="C:/project",
        total_files_discovered=5,
        python_files_analyzed=1,
        files=[context_file],
        failed_files=[failed_file],
    )
    assert project_context.project_path == "C:/project"
    assert project_context.total_files_discovered == 5
    assert project_context.python_files_analyzed == 1
    assert len(project_context.files) == 1
    assert len(project_context.failed_files) == 1
    assert project_context["total_files_discovered"] == 5


def test_project_intelligence_summary_construction() -> None:
    summary = ProjectIntelligenceSummary(
        total_files=10,
        python_files_analyzed=8,
        total_classes=4,
        total_functions=12,
        total_function_calls=15,
        total_dependencies=6,
        local_dependencies=4,
        external_dependencies=2,
    )

    assert summary.total_files == 10
    assert summary.python_files_analyzed == 8
    assert summary.total_classes == 4
    assert summary.total_functions == 12
    assert summary.total_function_calls == 15
    assert summary.total_dependencies == 6
    assert summary.local_dependencies == 4
    assert summary.external_dependencies == 2
    assert summary["python_files_analyzed"] == 8


def test_project_intelligence_model_construction() -> None:
    project_context = ProjectContext(
        project_path="C:/my_project",
        total_files_discovered=2,
        python_files_analyzed=1,
        files=[
            ContextFile(
                file_path="main.py",
                classes=[],
                functions=[ContextFunction(name="main", line=1, is_async=False)],
                imports=["os"],
            )
        ],
        failed_files=[],
    )

    dependencies = DependencyAnalysis(
        project_path="C:/my_project",
        total_python_files=1,
        total_dependencies=1,
        local_dependencies=0,
        external_dependencies=1,
        dependencies=[
            Dependency(
                source_file="main.py",
                imported_module="os",
                target_file=None,
                is_local=False,
                line=1,
            )
        ],
        failed_files=[],
    )

    code_relationships = [
        CodeRelationshipAnalysis(
            file_path="main.py",
            classes=[ClassRelationship(name="App", line=2, bases=["Base"])],
            functions=[
                FunctionRelationship(
                    name="run",
                    qualified_name="App.run",
                    line=3,
                    is_async=False,
                )
            ],
            function_calls=[FunctionCall(caller="run", callee="print", line=4)],
        )
    ]

    summary = ProjectIntelligenceSummary(
        total_files=2,
        python_files_analyzed=1,
        total_classes=0,
        total_functions=1,
        total_function_calls=1,
        total_dependencies=1,
        local_dependencies=0,
        external_dependencies=1,
    )

    intelligence = ProjectIntelligence(
        project_path="C:/my_project",
        project_context=project_context,
        dependencies=dependencies,
        code_relationships=code_relationships,
        summary=summary,
    )

    assert intelligence.project_path == "C:/my_project"
    assert intelligence.project_context.python_files_analyzed == 1
    assert intelligence.dependencies.total_dependencies == 1
    assert len(intelligence.code_relationships) == 1
    assert intelligence.summary.total_functions == 1
    assert intelligence["summary"]["total_functions"] == 1


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        ContextMethod(
            name="fn",
            line=1,
            is_async=False,
            extra_field="rejected",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        ProjectIntelligenceSummary(
            total_files=1,
            python_files_analyzed=1,
            total_classes=0,
            total_functions=0,
            total_function_calls=0,
            total_dependencies=0,
            local_dependencies=0,
            external_dependencies=0,
            unexpected_field=123,  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        ProjectContext(
            project_path="/path",
            total_files_discovered=1,
            python_files_analyzed=1,
            files=[],
            failed_files=[],
            extra_field="rejected",  # type: ignore[call-arg]
        )


def test_nested_model_validation() -> None:
    with pytest.raises(ValidationError):
        ContextMethod(
            name="test",
            line="invalid_line",  # type: ignore[arg-type]
            is_async=False,
        )

    with pytest.raises(ValidationError):
        ProjectIntelligenceSummary(  # type: ignore[call-arg]
            total_files=1,
            python_files_analyzed=1,
        )


def test_build_project_intelligence_integration(tmp_path: Path) -> None:
    pkg = tmp_path / "sample_app"
    pkg.mkdir()

    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "service.py").write_text(
        "class Service:\n    def execute(self) -> None:\n        pass\n",
        encoding="utf-8",
    )
    (pkg / "main.py").write_text(
        "from sample_app.service import Service\n\n"
        "def run():\n"
        "    s = Service()\n"
        "    s.execute()\n",
        encoding="utf-8",
    )
    (tmp_path / "notes.txt").write_text("documentation", encoding="utf-8")

    result = build_project_intelligence(tmp_path)

    assert isinstance(result, ProjectIntelligence)
    assert result.project_path == tmp_path.resolve().as_posix()
    assert isinstance(result.project_context, ProjectContext)
    assert isinstance(result.dependencies, DependencyAnalysis)
    assert isinstance(result.code_relationships, list)
    assert isinstance(result.summary, ProjectIntelligenceSummary)

    assert result.summary.total_files == 4
    assert result.summary.python_files_analyzed == 3
    assert result.summary.total_classes == 1
    assert result.summary.total_functions == 1
    assert result.summary.total_function_calls >= 1
    assert result.summary.local_dependencies >= 1

    # Dictionary access compatibility
    assert result["summary"]["total_classes"] == 1
    assert result["project_path"] == tmp_path.resolve().as_posix()


def test_api_response_compatibility_with_real_intelligence(
    tmp_path: Path,
) -> None:
    (tmp_path / "script.py").write_text(
        "def greet():\n    return 'hello'\n",
        encoding="utf-8",
    )

    client = TestClient(app)
    response = client.post(
        "/projects/intelligence",
        json={"project_path": str(tmp_path)},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["project_path"] == tmp_path.resolve().as_posix()
    assert "project_context" in data
    assert "dependencies" in data
    assert "code_relationships" in data
    assert "summary" in data
    assert data["summary"]["python_files_analyzed"] == 1
    assert data["summary"]["total_functions"] == 1
