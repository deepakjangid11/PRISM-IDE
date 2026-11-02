
import pytest

from prism.intelligence.code_relationships import (
    analyze_code_relationships,
)


def test_analyze_code_relationships() -> None:
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

    assert len(result["classes"]) == 2
    assert result["classes"][1]["bases"] == ["Parent"]

    function_names = [
        function["name"] for function in result["functions"]
    ]
    assert "run" in function_names
    assert "execute" in function_names
    assert "start" in function_names

    callees = [
        call["callee"] for call in result["function_calls"]
    ]
    assert "print" in callees
    assert "self.run" in callees
    assert "helper" in callees


def test_analyze_code_relationships_handles_empty_source() -> None:
    result = analyze_code_relationships("")

    assert result["classes"] == []
    assert result["functions"] == []
    assert result["function_calls"] == []


def test_analyze_code_relationships_rejects_invalid_syntax() -> None:
    with pytest.raises(ValueError, match="Invalid Python syntax"):
        analyze_code_relationships("def broken(:", "broken.py")
