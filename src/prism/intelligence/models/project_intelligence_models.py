from typing import Any

from pydantic import BaseModel, ConfigDict

from prism.intelligence.models.dependency_models import DependencyAnalysis
from prism.intelligence.models.relationship_models import (
    CodeRelationshipAnalysis,
)


class ContextMethod(BaseModel):
    """Represents a method within a class in the project context."""

    model_config = ConfigDict(extra="forbid")

    name: str
    line: int
    is_async: bool

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class ContextClass(BaseModel):
    """Represents a class definition in the project context."""

    model_config = ConfigDict(extra="forbid")

    name: str
    line: int
    methods: list[ContextMethod]

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class ContextFunction(BaseModel):
    """Represents a function definition in the project context."""

    model_config = ConfigDict(extra="forbid")

    name: str
    line: int
    is_async: bool

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class ContextFile(BaseModel):
    """Represents an analyzed Python file in the project context."""

    model_config = ConfigDict(extra="forbid")

    file_path: str
    classes: list[ContextClass]
    functions: list[ContextFunction]
    imports: list[str]

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class ContextFailedFile(BaseModel):
    """Represents a file that failed analysis in the project context."""

    model_config = ConfigDict(extra="forbid")

    file_path: str
    error: str

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class ProjectContext(BaseModel):
    """Structured context of discovered and analyzed files in a project."""

    model_config = ConfigDict(extra="forbid")

    project_path: str
    total_files_discovered: int
    python_files_analyzed: int
    files: list[ContextFile]
    failed_files: list[ContextFailedFile]

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class ProjectIntelligenceSummary(BaseModel):
    """Summary metrics of project intelligence analysis."""

    model_config = ConfigDict(extra="forbid")

    total_files: int
    python_files_analyzed: int
    total_classes: int
    total_functions: int
    total_function_calls: int
    total_dependencies: int
    local_dependencies: int
    external_dependencies: int

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class ProjectIntelligence(BaseModel):
    """Unified structural, dependency, and relationship intelligence."""

    model_config = ConfigDict(extra="forbid")

    project_path: str
    project_context: ProjectContext
    dependencies: DependencyAnalysis
    code_relationships: list[CodeRelationshipAnalysis]
    summary: ProjectIntelligenceSummary

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error
