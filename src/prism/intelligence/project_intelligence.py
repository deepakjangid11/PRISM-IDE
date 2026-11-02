
import sys
from pathlib import Path
from typing import Any

from prism.context.project_context import build_project_context
from prism.exceptions.custom_exception import CustomException
from prism.intelligence.code_relationships import analyze_code_relationships
from prism.intelligence.dependency_analyzer import (
    analyze_project_dependencies,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)

def build_project_intelligence(
    project_path: str | Path,
) -> dict[str, Any]:
    """Build unified structural and dependency intelligence for a project."""
    root = Path(project_path).expanduser().resolve()

    logger.info("Project intelligence started | root=%s", root)

    try:
        context = build_project_context(root)
        dependencies = analyze_project_dependencies(root)

        relationships: list[dict[str, Any]] = []

        for file_data in context["files"]:
            relative_path = file_data["file_path"]
            source_path = root / relative_path

            try:
                source_code = source_path.read_text(encoding="utf-8")

                relationship_data = analyze_code_relationships(
                    source_code,
                    relative_path,
                )

                relationships.append(relationship_data)

            except (OSError, UnicodeDecodeError, ValueError) as error:
                logger.warning(
                    "Relationship analysis failed | file=%s | error=%s",
                    relative_path,
                    error,
                )

        result: dict[str, Any] = {
            "project_path": root.as_posix(),
            "project_context": context,
            "dependencies": dependencies,
            "code_relationships": relationships,
            "summary": {
                "total_files": context["total_files_discovered"],
                "python_files_analyzed": context["python_files_analyzed"],
                "total_classes": sum(
                    len(file_data["classes"])
                    for file_data in context["files"]
                ),
                "total_functions": sum(
                    len(file_data["functions"])
                    for file_data in context["files"]
                ),
                "total_function_calls": sum(
                    len(file_data["function_calls"])
                    for file_data in relationships
                ),
                "total_dependencies": dependencies["total_dependencies"],
                "local_dependencies": dependencies["local_dependencies"],
                "external_dependencies": dependencies["external_dependencies"],
            },
        }

        logger.info(
            "Project intelligence completed | files=%s | functions=%s "
            "| dependencies=%s",
            result["summary"]["python_files_analyzed"],
            result["summary"]["total_functions"],
            result["summary"]["total_dependencies"],
        )

        return result

    except Exception as error:
        logger.exception("Project intelligence generation failed")
        raise CustomException(error, sys) from error
