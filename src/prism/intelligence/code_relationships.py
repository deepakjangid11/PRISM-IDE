import ast
import sys
from pathlib import Path

from prism.exceptions.custom_exception import CustomException
from prism.intelligence.models.relationship_models import (
    ClassRelationship,
    CodeRelationshipAnalysis,
    FunctionCall,
    FunctionRelationship,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class CodeRelationshipVisitor(ast.NodeVisitor):
    """Extract class, function, and function-call relationships."""

    def __init__(self) -> None:
        self.classes: list[ClassRelationship] = []
        self.functions: list[FunctionRelationship] = []
        self.function_calls: list[FunctionCall] = []
        self._scope_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(
            ClassRelationship(
                name=node.name,
                line=node.lineno,
                bases=[ast.unparse(base) for base in node.bases],
            )
        )

        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool,
    ) -> None:
        qualified_name = ".".join([*self._scope_stack, node.name])

        self.functions.append(
            FunctionRelationship(
                name=node.name,
                qualified_name=qualified_name,
                line=node.lineno,
                is_async=is_async,
            )
        )

        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        caller = self._current_scope()

        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee = ast.unparse(node.func)
        else:
            callee = ast.unparse(node.func)

        self.function_calls.append(
            FunctionCall(
                caller=caller,
                callee=callee,
                line=node.lineno,
            )
        )

        self.generic_visit(node)

    def _current_scope(self) -> str:
        if not self._scope_stack:
            return "<module>"

        return ".".join(self._scope_stack)


def analyze_code_relationships(
    source_code: str,
    file_path: str = "<unknown>",
) -> CodeRelationshipAnalysis:
    """Analyze Python definitions, inheritance, and function calls."""
    logger.info("Code relationship analysis started | file=%s", file_path)

    try:
        tree = ast.parse(source_code, filename=file_path)
        visitor = CodeRelationshipVisitor()
        visitor.visit(tree)

        result = CodeRelationshipAnalysis(
            file_path=file_path,
            classes=visitor.classes,
            functions=visitor.functions,
            function_calls=visitor.function_calls,
        )

        logger.info(
            "Code relationship analysis completed | file=%s | classes=%s "
            "| functions=%s | calls=%s",
            file_path,
            len(visitor.classes),
            len(visitor.functions),
            len(visitor.function_calls),
        )

        return result

    except SyntaxError as error:
        logger.warning(
            "Invalid Python syntax | file=%s | line=%s",
            file_path,
            error.lineno,
        )
        raise ValueError(
            f"Invalid Python syntax in {file_path} at line {error.lineno}: {error.msg}"
        ) from error

    except Exception as error:
        logger.exception(
            "Code relationship analysis failed | file=%s",
            file_path,
        )
        raise CustomException(error, sys) from error


def analyze_python_file(
    file_path: str | Path,
) -> CodeRelationshipAnalysis:
    """Analyze a Python file and return its relationships."""
    path = Path(file_path)

    if not path.is_file():
        raise ValueError(f"Invalid Python file: {path}")

    if path.suffix != ".py":
        raise ValueError(f"File is not a Python file: {path}")

    try:
        source_code = path.read_text(encoding="utf-8")
        return analyze_code_relationships(
            source_code=source_code,
            file_path=path.as_posix(),
        )

    except UnicodeDecodeError as error:
        logger.warning(
            "Python file is not valid UTF-8 | file=%s",
            path,
        )
        raise ValueError(f"Unable to decode Python file as UTF-8: {path}") from error

    except OSError as error:
        logger.exception(
            "Unable to read Python file | file=%s",
            path,
        )
        raise CustomException(error, sys) from error
