from pydantic import BaseModel, ConfigDict


class ClassRelationship(BaseModel):
    """Represents a class and its inheritance relationships."""

    model_config = ConfigDict(extra="forbid")

    name: str
    line: int
    bases: list[str]


class FunctionRelationship(BaseModel):
    """Represents a function or method definition."""

    model_config = ConfigDict(extra="forbid")

    name: str
    qualified_name: str
    line: int
    is_async: bool


class FunctionCall(BaseModel):
    """Represents a function call relationship."""

    model_config = ConfigDict(extra="forbid")

    caller: str
    callee: str
    line: int


class CodeRelationshipAnalysis(BaseModel):
    """Structured result of code relationship analysis."""

    model_config = ConfigDict(extra="forbid")

    file_path: str
    classes: list[ClassRelationship]
    functions: list[FunctionRelationship]
    function_calls: list[FunctionCall]
