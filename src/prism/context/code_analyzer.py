import ast
import sys
from pathlib import Path
from typing import Any

from prism.exceptions.custom_exception import CustomException
from prism.logging.logger import get_logger

logger = get_logger(__name__)


def analyze_python_code(
    source_code: str,
    file_path: str = "<unknown>",
) -> dict[str, Any]:
    """Extract classes, functions, methods, and imports from Python source."""
    logger.info("Python code analysis started | file=%s", file_path)

    try:
        tree = ast.parse(source_code, filename=file_path)

        classes: list[dict[str, Any]] = []
        functions: list[dict[str, Any]] = []
        imports: list[str] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = [
                    {
                        "name": item.name,
                        "line": item.lineno,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                    }
                    for item in node.body
                    if isinstance(
                        item,
                        (ast.FunctionDef, ast.AsyncFunctionDef),
                    )
                ]

                classes.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods,
                    }
                )

            elif isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                functions.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    }
                )

            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)

            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                imports.append(module)

        result: dict[str, Any] = {
            "file_path": file_path,
            "classes": classes,
            "functions": functions,
            "imports": sorted(set(imports)),
        }

        logger.info(
            "Python code analysis completed | file=%s | classes=%s "
            "| functions=%s | imports=%s",
            file_path,
            len(classes),
            len(functions),
            len(imports),
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
            "Python code analysis failed | file=%s",
            file_path,
        )
        raise CustomException(error, sys) from error


def analyze_python_file(
    file_path: str | Path,
) -> dict[str, Any]:
    """Read a UTF-8 Python file and analyze its structure."""
    path = Path(file_path)

    try:
        source_code = path.read_text(encoding="utf-8")
        return analyze_python_code(source_code, str(path))

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
