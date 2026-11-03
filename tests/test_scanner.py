import logging
from pathlib import Path

import pytest

from prism.context import project_scanner
from prism.context.project_scanner import scan_project


def test_scan_project_returns_relative_file_paths(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "print('app')",
        encoding="utf-8",
    )

    result = scan_project(tmp_path)

    assert result == ["main.py", "src/app.py"]


def test_scan_project_ignores_excluded_directories(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text("pass", encoding="utf-8")

    ignored_dir = tmp_path / ".venv"
    ignored_dir.mkdir()
    (ignored_dir / "ignored.py").write_text("pass", encoding="utf-8")

    result = scan_project(tmp_path)

    assert result == ["main.py"]


def test_scan_project_ignores_env_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text("pass", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=value", encoding="utf-8")
    (tmp_path / ".env.local").write_text("SECRET=value", encoding="utf-8")
    (tmp_path / ".env.production").write_text(
        "SECRET=value",
        encoding="utf-8",
    )

    result = scan_project(tmp_path)

    assert result == ["main.py"]


def test_scan_project_raises_for_missing_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        scan_project(tmp_path / "does_not_exist")


def test_scan_project_raises_for_file_path(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "main.py"
    file_path.write_text("pass", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        scan_project(file_path)


def test_scan_project_logs_start_and_completion(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (tmp_path / "main.py").write_text("pass", encoding="utf-8")

    with caplog.at_level(
        logging.INFO,
        logger="prism.context.project_scanner",
    ):
        result = scan_project(tmp_path)

    assert result == ["main.py"]
    assert "Project scan started" in caplog.text
    assert "Project scan completed" in caplog.text


def test_scan_project_respects_file_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (tmp_path / "a.py").write_text("pass", encoding="utf-8")
    (tmp_path / "b.py").write_text("pass", encoding="utf-8")
    monkeypatch.setattr(project_scanner, "MAX_FILES", 1)

    with caplog.at_level(
        logging.WARNING,
        logger="prism.context.project_scanner",
    ):
        result = scan_project(tmp_path)

    assert len(result) == 1
    assert "Project scan reached file limit" in caplog.text


def test_scan_project_does_not_follow_symlink_directories(
    tmp_path: Path,
) -> None:
    actual_dir = tmp_path / "actual"
    actual_dir.mkdir()
    (actual_dir / "inside.py").write_text("pass", encoding="utf-8")

    link_dir = tmp_path / "linked"

    try:
        link_dir.symlink_to(actual_dir, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("Directory symlinks are unavailable on this system")

    result = scan_project(tmp_path)

    assert "actual/inside.py" in result
    assert "linked/inside.py" not in result
