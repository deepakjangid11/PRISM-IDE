from pathlib import Path

from prism.context.project_context import build_project_context


def test_build_project_context_analyzes_python_files(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text(
        "import os\n\nclass Example:\n    def run(self):\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "notes.txt").write_text("Not Python", encoding="utf-8")

    result = build_project_context(tmp_path)

    assert result["total_files_discovered"] == 2
    assert result["python_files_analyzed"] == 1
    assert result["failed_files"] == []
    assert result["files"][0]["classes"][0]["name"] == "Example"
    assert result["files"][0]["classes"][0]["methods"][0]["name"] == "run"
    assert result["files"][0]["imports"] == ["os"]


def test_build_project_context_reports_invalid_python(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def broken(:", encoding="utf-8")

    result = build_project_context(tmp_path)

    assert result["python_files_analyzed"] == 0
    assert len(result["failed_files"]) == 1
    assert result["failed_files"][0]["file_path"] == "broken.py"
