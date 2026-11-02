
import pytest

from prism.context.code_analyzer import analyze_python_code


def test_analyze_python_code_extracts_structure() -> None:
    source = """
import os
from pathlib import Path

class Scanner:
    def scan(self):
        pass

def build():
    pass

async def fetch():
    pass
"""

    result = analyze_python_code(source, "scanner.py")

    assert result["file_path"] == "scanner.py"
    assert [item["name"] for item in result["classes"]] == ["Scanner"]
    assert result["classes"][0]["methods"][0]["name"] == "scan"
    assert [item["name"] for item in result["functions"]] == [
        "build",
        "fetch",
    ]
    assert result["functions"][1]["is_async"] is True
    assert result["imports"] == ["os", "pathlib"]


def test_analyze_python_code_rejects_invalid_syntax() -> None:
    with pytest.raises(ValueError, match="Invalid Python syntax"):
        analyze_python_code("def broken(:", "broken.py")


def test_analyze_python_code_handles_empty_source() -> None:
    result = analyze_python_code("", "empty.py")

    assert result["classes"] == []
    assert result["functions"] == []
    assert result["imports"] == []
