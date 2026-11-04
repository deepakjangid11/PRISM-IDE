import pytest
from pydantic import ValidationError

from prism.learning.models import (
    KnowledgeGap,
    KnowledgeGapType,
    LearningPath,
    LearningProgress,
    LearningRecommendation,
)


def test_knowledge_gap_model_and_getitem() -> None:
    gap = KnowledgeGap(
        gap_id="gap-1",
        developer_id="dev-1",
        target_skill="Machine Learning",
        missing_skill="NumPy",
        gap_type=KnowledgeGapType.MISSING_PREREQUISITE,
        description="Missing NumPy prerequisite",
        severity="high",
    )
    assert gap["target_skill"] == "Machine Learning"
    assert gap["missing_skill"] == "NumPy"
    assert gap["severity"] == "high"

    with pytest.raises(KeyError):
        _ = gap["unknown_field"]


def test_learning_recommendation_model_and_extra_forbid() -> None:
    rec = LearningRecommendation(
        recommendation_id="rec-1",
        developer_id="dev-1",
        skill_name="Python",
        title="Learn Python",
        description="Core language",
        priority=1,
        suggested_action="Read tutorial",
    )
    assert rec["skill_name"] == "Python"
    assert rec.priority == 1

    with pytest.raises(ValidationError):
        LearningRecommendation(
            recommendation_id="rec-1",
            developer_id="dev-1",
            skill_name="Python",
            title="Learn Python",
            description="Core language",
            priority=1,
            suggested_action="Read tutorial",
            extra="not_allowed",  # type: ignore[call-arg]
        )


def test_learning_path_and_progress_models() -> None:
    path = LearningPath(
        path_id="path-1",
        developer_id="dev-1",
        target_goal="FastAPI",
        steps=["Python", "FastAPI"],
        estimated_steps=2,
    )
    assert path.steps == ["Python", "FastAPI"]
    assert path["target_goal"] == "FastAPI"

    progress = LearningProgress(
        developer_id="dev-1",
        target_goal="FastAPI",
        completed_skills=["Python"],
        in_progress_skills=[],
        remaining_skills=["FastAPI"],
        completion_percentage=50.0,
    )
    assert progress.completion_percentage == 50.0
    assert progress["completed_skills"] == ["Python"]
