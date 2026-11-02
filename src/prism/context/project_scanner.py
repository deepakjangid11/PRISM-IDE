
import os
import sys
from pathlib import Path

from prism.exceptions.custom_exception import CustomException
from prism.logging.logger import get_logger

logger = get_logger(__name__)

IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}

MAX_FILES = 10_000


def _raise_walk_error(error: OSError) -> None:
    """Propagate filesystem errors encountered during directory traversal."""
    raise error


def scan_project(project_path: str | Path) -> list[str]:
    """Return sorted, relative file paths discovered in a project directory."""
    try:
        root = Path(project_path).expanduser().resolve()

        if not root.exists():
            logger.warning(
                "Project scan rejected: path does not exist | root=%s",
                root,
            )
            raise FileNotFoundError(f"Project path does not exist: {root}")

        if not root.is_dir():
            logger.warning(
                "Project scan rejected: path is not a directory | root=%s",
                root,
            )
            raise NotADirectoryError(
                f"Project path is not a directory: {root}"
            )

        logger.info("Project scan started | root=%s", root)

        discovered_files: list[str] = []

        for current_path, directories, filenames in os.walk(
            root,
            topdown=True,
            followlinks=False,
            onerror=_raise_walk_error,
        ):
            current_directory = Path(current_path)

            directories[:] = sorted(
                directory
                for directory in directories
                if directory not in IGNORED_DIRECTORIES
                and not (current_directory / directory).is_symlink()
            )

            for filename in sorted(filenames):
                if filename == ".env" or filename.startswith(".env."):
                    logger.debug(
                        "Skipping environment file | filename=%s",
                        filename,
                    )
                    continue

                file_path = current_directory / filename

                if file_path.is_symlink() or not file_path.is_file():
                    continue

                relative_path = file_path.relative_to(root).as_posix()
                discovered_files.append(relative_path)

                if len(discovered_files) >= MAX_FILES:
                    logger.warning(
                        "Project scan reached file limit | root=%s | limit=%s",
                        root,
                        MAX_FILES,
                    )
                    return discovered_files

        logger.info(
            "Project scan completed | root=%s | files=%s",
            root,
            len(discovered_files),
        )
        return discovered_files

    except (FileNotFoundError, NotADirectoryError):
        raise
    except OSError as error:
        logger.exception("Project scan failed due to filesystem error")
        raise CustomException(error, sys) from error
