from prism.intelligence.models.relationship_models import (
    ClassRelationship,
    CodeRelationshipAnalysis,
    FunctionCall,
    FunctionRelationship,
)


def test_class_relationship_model() -> None:
    result = ClassRelationship(
        name="Developer",
        line=10,
        bases=["BaseDeveloper"],
    )

    assert result.name == "Developer"
    assert result.line == 10
    assert result.bases == ["BaseDeveloper"]


def test_function_relationship_model() -> None:
    result = FunctionRelationship(
        name="calculate",
        qualified_name="Developer.calculate",
        line=20,
        is_async=False,
    )

    assert result.name == "calculate"
    assert result.qualified_name == "Developer.calculate"
    assert result.line == 20
    assert result.is_async is False


def test_function_call_model() -> None:
    result = FunctionCall(
        caller="main",
        callee="calculate",
        line=30,
    )

    assert result.caller == "main"
    assert result.callee == "calculate"
    assert result.line == 30


def test_code_relationship_analysis_model() -> None:
    result = CodeRelationshipAnalysis(
        file_path="app/main.py",
        classes=[
            ClassRelationship(
                name="Developer",
                line=10,
                bases=[],
            )
        ],
        functions=[
            FunctionRelationship(
                name="main",
                qualified_name="main",
                line=20,
                is_async=False,
            )
        ],
        function_calls=[
            FunctionCall(
                caller="main",
                callee="calculate",
                line=25,
            )
        ],
    )

    assert result.file_path == "app/main.py"
    assert len(result.classes) == 1
    assert len(result.functions) == 1
    assert len(result.function_calls) == 1
