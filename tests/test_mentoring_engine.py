from datetime import UTC, datetime

import pytest

from prism.intelligence.models.dependency_models import (
    Dependency,
    DependencyAnalysis,
)
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.project_intelligence_models import (
    ProjectContext,
    ProjectIntelligence,
    ProjectIntelligenceSummary,
)
from prism.mentoring.engine import MentoringEngine
from prism.mentoring.models import (
    MentorContext,
    MentorMode,
    MentorRequest,
    MentorResponse,
)


def make_project_intelligence() -> ProjectIntelligence:
    summary = ProjectIntelligenceSummary(
        total_files=4,
        python_files_analyzed=3,
        total_classes=2,
        total_functions=5,
        total_function_calls=6,
        total_dependencies=2,
        local_dependencies=1,
        external_dependencies=1,
    )
    context = ProjectContext(
        project_path="/sample/proj",
        total_files_discovered=4,
        python_files_analyzed=3,
        files=[],
        failed_files=[],
    )
    dependencies = DependencyAnalysis(
        project_path="/sample/proj",
        total_python_files=3,
        total_dependencies=2,
        local_dependencies=1,
        external_dependencies=1,
        dependencies=[
            Dependency(
                source_file="main.py",
                imported_module="fastapi",
                is_local=False,
                line=1,
            )
        ],
        failed_files=[],
    )
    return ProjectIntelligence(
        project_path="/sample/proj",
        project_context=context,
        dependencies=dependencies,
        code_relationships=[],
        summary=summary,
    )


def test_build_mode_mentoring_with_project_intelligence() -> None:
    engine = MentoringEngine()
    proj_intel = make_project_intelligence()

    req = MentorRequest(
        developer_id="dev_builder",
        mode=MentorMode.BUILD,
        query="How is my project dependency structure?",
        project_path="/sample/proj",
    )

    response = engine.mentor(req, project_intelligence=proj_intel)

    assert response.mode == MentorMode.BUILD
    assert response.developer_id == "dev_builder"
    assert len(response.recommendations) >= 1
    assert any(r.category == "dependencies" for r in response.recommendations)
    assert len(response.actionable_next_steps) >= 1


def test_build_mode_with_behavior_insights() -> None:
    engine = MentoringEngine()
    now = datetime.now(UTC)
    activities = [
        DeveloperActivity(
            event_id="e1",
            developer_id="dev_tester",
            event_type="test_run",
            timestamp=now,
            project_path="/sample/proj",
        ),
        DeveloperActivity(
            event_id="e2",
            developer_id="dev_tester",
            event_type="test_failure",
            timestamp=now,
            project_path="/sample/proj",
        ),
        DeveloperActivity(
            event_id="e3",
            developer_id="dev_tester",
            event_type="test_run",
            timestamp=now,
            project_path="/sample/proj",
        ),
        DeveloperActivity(
            event_id="e4",
            developer_id="dev_tester",
            event_type="test_failure",
            timestamp=now,
            project_path="/sample/proj",
        ),
        DeveloperActivity(
            event_id="e5",
            developer_id="dev_tester",
            event_type="test_run",
            timestamp=now,
            project_path="/sample/proj",
        ),
        DeveloperActivity(
            event_id="e6",
            developer_id="dev_tester",
            event_type="test_failure",
            timestamp=now,
            project_path="/sample/proj",
        ),
    ]

    req = MentorRequest(
        developer_id="dev_tester",
        mode=MentorMode.BUILD,
        query="Why are my builds struggling?",
        project_path="/sample/proj",
    )

    response = engine.mentor(req, activities=activities)

    assert any(r.category == "testing" for r in response.recommendations)
    assert any("test" in step.lower() for step in response.actionable_next_steps)


def test_learn_mode_mentoring_with_target_skill() -> None:
    engine = MentoringEngine()

    req = MentorRequest(
        developer_id="dev_learner",
        mode=MentorMode.LEARN,
        query="I want to learn Machine Learning",
        target_skill="Machine Learning",
    )

    response = engine.mentor(req)

    assert response.mode == MentorMode.LEARN
    assert len(response.recommendations) >= 1
    # Check that actionable steps contain steps towards learning
    assert any("python" in step.lower() for step in response.actionable_next_steps)
    assert response.context_used["knowledge_gaps_count"] > 0


def test_learn_mode_infers_skill_from_query() -> None:
    engine = MentoringEngine()

    req = MentorRequest(
        developer_id="dev_learner",
        mode=MentorMode.LEARN,
        query="Can you teach me FastAPI?",
    )

    response = engine.mentor(req)

    assert response.mode == MentorMode.LEARN
    assert any(
        "fastapi" in r.title.lower() or "python" in r.title.lower()
        for r in response.recommendations
    )


def test_custom_generator_injection() -> None:
    class MockGenerator:
        def generate(self, context: MentorContext) -> MentorResponse:
            return MentorResponse(
                response_id="custom-1",
                developer_id=context.developer_id,
                mode=context.mode,
                summary="Mocked AI response",
                explanation="LLM-ready mock output",
                recommendations=[],
                actionable_next_steps=["Step 1"],
            )

    engine = MentoringEngine(generator=MockGenerator())
    req = MentorRequest(
        developer_id="dev1",
        mode=MentorMode.BUILD,
        query="Custom request",
    )
    response = engine.mentor(req)

    assert response.response_id == "custom-1"
    assert response.summary == "Mocked AI response"


def test_invalid_request_validation() -> None:
    engine = MentoringEngine()
    req_empty_dev = MentorRequest(
        developer_id="   ",
        mode=MentorMode.BUILD,
        query="test query",
    )
    with pytest.raises(ValueError, match="Developer ID cannot be empty"):
        engine.mentor(req_empty_dev)

    req_empty_query = MentorRequest(
        developer_id="dev1",
        mode=MentorMode.BUILD,
        query="   ",
    )
    with pytest.raises(ValueError, match="Query cannot be empty"):
        engine.mentor(req_empty_query)
