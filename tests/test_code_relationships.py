from pathlib import Path

import pytest

from prism.intelligence.code_relationships import (
    analyze_code_relationships,
    analyze_python_file,
)


def test_analyze_code_relationships_classes_and_inheritance() -> None:
    source = """
class Parent:
    pass


class Child(Parent):
    pass
"""
    result = analyze_code_relationships(source, "example.py")

    assert result.file_path == "example.py"
    assert len(result.classes) == 2
    assert result.classes[0].name == "Parent"
    assert result.classes[0].bases == []
    assert result.classes[1].name == "Child"
    assert result.classes[1].bases == ["Parent"]


def test_analyze_code_relationships_functions_and_calls() -> None:
    source = """
class Parent:
    def run(self):
        print("Running")


class Child(Parent):
    def execute(self):
        self.run()


def start():
    helper()


def helper():
    pass
"""
    result = analyze_code_relationships(source, "example.py")

    assert len(result.classes) == 2
    assert result.classes[1].bases == ["Parent"]

    function_names = [function.name for function in result.functions]
    assert "run" in function_names
    assert "execute" in function_names
    assert "start" in function_names
    assert "helper" in function_names

    callees = [call.callee for call in result.function_calls]
    assert "print" in callees
    assert "self.run" in callees
    assert "helper" in callees

    callers = [call.caller for call in result.function_calls]
    assert "Parent.run" in callers
    assert "Child.execute" in callers
    assert "start" in callers


def test_analyze_code_relationships_handles_empty_source() -> None:
    result = analyze_code_relationships("")

    assert result.file_path == "<unknown>"
    assert result.classes == []
    assert result.functions == []
    assert result.function_calls == []


def test_analyze_code_relationships_rejects_invalid_syntax() -> None:
    with pytest.raises(ValueError, match="Invalid Python syntax"):
        analyze_code_relationships("def broken(:", "broken.py")


def test_analyze_code_relationships_async_and_qualified_names() -> None:
    source = """
class Service:
    async def fetch(self):
        pass

    class SubService:
        def process(self):
            pass


async def main():
    pass
"""
    result = analyze_code_relationships(source, "service.py")

    assert len(result.functions) == 3

    func_map = {f.name: f for f in result.functions}
    assert func_map["fetch"].is_async is True
    assert func_map["fetch"].qualified_name == "Service.fetch"

    assert func_map["process"].is_async is False
    assert func_map["process"].qualified_name == "Service.SubService.process"

    assert func_map["main"].is_async is True
    assert func_map["main"].qualified_name == "main"


def test_analyze_python_file(tmp_path: Path) -> None:
    file_path = tmp_path / "valid.py"
    file_path.write_text(
        "class Model:\n    def save(self):\n        pass\n",
        encoding="utf-8",
    )

    result = analyze_python_file(file_path)

    assert result.file_path == file_path.as_posix()
    assert len(result.classes) == 1
    assert result.classes[0].name == "Model"
    assert len(result.functions) == 1
    assert result.functions[0].qualified_name == "Model.save"


def test_analyze_python_file_rejects_invalid_path(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.py"
    with pytest.raises(ValueError, match="Invalid Python file"):
        analyze_python_file(missing_file)


def test_analyze_python_file_rejects_non_python_extension(
    tmp_path: Path,
) -> None:
    text_file = tmp_path / "readme.txt"
    text_file.write_text("Hello", encoding="utf-8")
    with pytest.raises(ValueError, match="File is not a Python file"):
        analyze_python_file(text_file)


def test_analyze_python_file_rejects_invalid_utf8(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.py"
    bad_file.write_bytes(b"\x80\x81")
    with pytest.raises(ValueError, match="Unable to decode Python file as UTF-8"):
        analyze_python_file(bad_file)
