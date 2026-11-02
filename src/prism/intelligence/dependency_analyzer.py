
import ast
import sys
from pathlib import Path
from typing import Any

from prism.exceptions.custom_exception import CustomException
from prism.logging.logger import get_logger

logger = get_logger(__name__)

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
}


def _get_module_name(relative_path: str) -> str:
    """Convert a Python file path into its importable module name."""
    path = Path(relative_path)
    parts = list(path.with_suffix("").parts)

    if parts and parts[0] == "src":
        parts.pop(0)

    if parts and parts[-1] == "__init__":
        parts.pop()

    return ".".join(parts)


def _resolve_relative_import(
    current_module: str,
    is_package: bool,
    level: int,
    module: str | None,
) -> str | None:
    """Resolve absolute and relative imports."""
    if level == 0:
        return module

    package_parts = current_module.split(".")

    if not is_package:
        package_parts.pop()

    if level > len(package_parts):
        return None

    base_parts = package_parts[: len(package_parts) - level + 1]

    if module:
        base_parts.extend(module.split("."))

    return ".".join(base_parts)


def analyze_project_dependencies(
    project_path: str | Path,
) -> dict[str, Any]:
    """Analyze local Python imports and cross-file dependencies."""
    root = Path(project_path).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError(f"Invalid project directory: {root}")

    logger.info("Dependency analysis started | root=%s", root)

    try:
        python_files = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*.py")
            if path.is_file()
            and not path.is_symlink()
            and not any(
                part in IGNORED_DIRECTORIES
                for part in path.relative_to(root).parts
            )
        )

        module_map = {
            _get_module_name(relative_path): relative_path
            for relative_path in python_files
            if _get_module_name(relative_path)
        }

        dependencies: list[dict[str, Any]] = []
        failed_files: list[dict[str, str]] = []

        for relative_path in python_files:
            file_path = root / relative_path

            try:
                source = file_path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=relative_path)

                current_module = _get_module_name(relative_path)
                is_package = file_path.name == "__init__.py"

                imported_modules: dict[str, int] = {}

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_modules[alias.name] = node.lineno

                    elif isinstance(node, ast.ImportFrom):
                        base_module = _resolve_relative_import(
                            current_module,
                            is_package,
                            node.level,
                            node.module,
                        )

                        if base_module is None:
                            continue

                        for alias in node.names:
                            if alias.name == "*":
                                resolved_module = base_module
                            else:
                                candidate = (
                                    f"{base_module}.{alias.name}"
                                    if base_module
                                    else alias.name
                                )

                                resolved_module = (
                                    candidate
                                    if candidate in module_map
                                    else base_module
                                )

                            if resolved_module:
                                imported_modules[resolved_module] = (
                                    node.lineno
                                )

                for imported_module, line_number in imported_modules.items():
                    resolved_file = module_map.get(imported_module)

                    dependencies.append(
                        {
                            "source_file": relative_path,
                            "imported_module": imported_module,
                            "target_file": resolved_file,
                            "is_local": resolved_file is not None,
                            "line": line_number,
                        }
                    )

            except (SyntaxError, UnicodeDecodeError, OSError) as error:
                logger.warning(
                    "Dependency analysis failed | file=%s | error=%s",
                    relative_path,
                    error,
                )

                failed_files.append(
                    {
                        "file_path": relative_path,
                        "error": str(error),
                    }
                )

        local_count = sum(
            1 for dependency in dependencies if dependency["is_local"]
        )

        result: dict[str, Any] = {
            "project_path": root.as_posix(),
            "total_python_files": len(python_files),
            "total_dependencies": len(dependencies),
            "local_dependencies": local_count,
            "external_dependencies": len(dependencies) - local_count,
            "dependencies": dependencies,
            "failed_files": failed_files,
        }

        logger.info(
            "Dependency analysis completed | files=%s | dependencies=%s "
            "| local=%s | external=%s",
            len(python_files),
            len(dependencies),
            local_count,
            len(dependencies) - local_count,
        )

        return result

    except ValueError:
        raise
    except Exception as error:
        logger.exception("Project dependency analysis failed")
        raise CustomException(error, sys) from error
