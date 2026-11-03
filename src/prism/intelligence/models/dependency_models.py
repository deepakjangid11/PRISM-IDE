from pydantic import BaseModel, ConfigDict


class Dependency(BaseModel):
    """Represents a single Python dependency."""

    model_config = ConfigDict(extra="forbid")

    source_file: str
    imported_module: str
    target_file: str | None = None
    is_local: bool
    line: int


class FailedDependencyFile(BaseModel):
    """Represents a Python file whose dependency analysis failed."""

    model_config = ConfigDict(extra="forbid")

    file_path: str
    error: str


class DependencyAnalysis(BaseModel):
    """Structured result of project dependency analysis."""

    model_config = ConfigDict(extra="forbid")

    project_path: str
    total_python_files: int
    total_dependencies: int
    local_dependencies: int
    external_dependencies: int
    dependencies: list[Dependency]
    failed_files: list[FailedDependencyFile]
