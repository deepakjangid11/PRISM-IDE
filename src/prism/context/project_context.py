from pathlib import Path
from typing import Any

from prism.context.code_analyzer import analyze_python_file
from prism.context.project_scanner import scan_project
from prism.logging.logger import get_logger

logger = get_logger(__name__)


def build_project_context(project_path: str | Path) -> dict[str, Any]:
    """Scan a project and collect structural information from Python files."""
    root = Path(project_path).expanduser().resolve()
    logger.info("Project context generation started | root=%s", root)

    files = scan_project(root)
    analyzed_files: list[dict[str, Any]] = []
    failed_files: list[dict[str, str]] = []

    for relative_path in files:
        if Path(relative_path).suffix.lower() != ".py":
            continue

        try:
            analyzed_files.append(analyze_python_file(root / relative_path))
        except (ValueError, OSError) as error:
            logger.warning(
                "Project file analysis failed | file=%s | error=%s",
                relative_path,
                error,
            )
            failed_files.append({"file_path": relative_path, "error": str(error)})

    result: dict[str, Any] = {
        "project_path": root.as_posix(),
        "total_files_discovered": len(files),
        "python_files_analyzed": len(analyzed_files),
        "files": analyzed_files,
        "failed_files": failed_files,
    }

    logger.info(
        "Project context generation completed | root=%s | analyzed=%s | failed=%s",
        root,
        len(analyzed_files),
        len(failed_files),
    )
    return result
