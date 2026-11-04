import pytest
from pydantic import ValidationError

from prism.mentoring.models import (
    MentorContext,
    MentorMode,
    MentorRecommendation,
    MentorRequest,
    MentorResponse,
)


def test_mentor_request_validation() -> None:
    req = MentorRequest(
        developer_id="dev-1",
        mode=MentorMode.BUILD,
        query="How should I structure my database layer?",
        project_path="/projects/sample",
    )
    assert req.mode == MentorMode.BUILD
    assert req.developer_id == "dev-1"

    with pytest.raises(ValidationError):
        MentorRequest(
            developer_id="dev-1",
            mode="invalid_mode",  # type: ignore[arg-type]
            query="test",
        )


def test_mentor_recommendation_and_response_models() -> None:
    rec = MentorRecommendation(
        recommendation_id="rec-1",
        category="architecture",
        title="Decouple API layer",
        details="Separate business logic from FastAPI routes",
        actionable_steps=["Move queries to service layer"],
        evidence=["FastAPI routes directly query DB"],
    )
    assert rec["category"] == "architecture"

    with pytest.raises(KeyError):
        _ = rec["missing_key"]

    resp = MentorResponse(
        response_id="resp-1",
        developer_id="dev-1",
        mode=MentorMode.BUILD,
        summary="Architecture review",
        explanation="Guidance on service layer",
        recommendations=[rec],
        actionable_next_steps=["Refactor routes"],
    )
    assert resp["summary"] == "Architecture review"
    assert len(resp.recommendations) == 1


def test_mentor_context_model() -> None:
    ctx = MentorContext(
        developer_id="dev-1",
        mode=MentorMode.LEARN,
        query="Explain Machine Learning",
    )
    assert ctx["mode"] == MentorMode.LEARN
    assert ctx.knowledge_gaps == []
