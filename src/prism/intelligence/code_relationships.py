
import ast
import sys
from typing import Any

from prism.exceptions.custom_exception import CustomException
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class CodeRelationshipVisitor(ast.NodeVisitor):
    """Extract definitions, inheritance, and function-call relationships."""

    def __init__(self) -> None:
        self.functions: list[dict[str, Any]] = []
        self.classes: list[dict[str, Any]] = []
        self.function_calls: list[dict[str, Any]] = []
        self.scope: list[str] = []

    def _current_scope(self) -> str:
        return ".".join(self.scope) if self.scope else "<module>"

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_name = node.name

        self.classes.append(
            {
                "name": class_name,
                "line": node.lineno,
                "bases": [ast.unparse(base) for base in node.bases],
            }
        )

        self.scope.append(class_name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool,
    ) -> None:
        qualified_name = ".".join([*self.scope, node.name])

        self.functions.append(
            {
                "name": node.name,
                "qualified_name": qualified_name,
                "line": node.lineno,
                "is_async": is_async,
            }
        )

        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            called_function = node.func.id
        elif isinstance(node.func, ast.Attribute):
            called_function = ast.unparse(node.func)
        else:
            called_function = ast.unparse(node.func)

        self.function_calls.append(
            {
                "caller": self._current_scope(),
                "callee": called_function,
                "line": node.lineno,
            }
        )

        self.generic_visit(node)


def analyze_code_relationships(
    source_code: str,
    file_path: str = "<unknown>",
) -> dict[str, Any]:
    """Analyze Python definitions, inheritance, and function calls."""
    logger.info("Code relationship analysis started | file=%s", file_path)

    try:
        tree = ast.parse(source_code, filename=file_path)
        visitor = CodeRelationshipVisitor()
        visitor.visit(tree)

        result: dict[str, Any] = {
            "file_path": file_path,
            "classes": visitor.classes,
            "functions": visitor.functions,
            "function_calls": visitor.function_calls,
        }

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
            f"Invalid Python syntax in {file_path} "
            f"at line {error.lineno}: {error.msg}"
        ) from error

    except Exception as error:
        logger.exception(
            "Code relationship analysis failed | file=%s",
            file_path,
        )
        raise CustomException(error, sys) from error
