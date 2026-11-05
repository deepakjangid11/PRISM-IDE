from datetime import UTC, datetime

import pytest

from prism.intelligence.models.developer_behavior_models import DeveloperActivity
from prism.intelligence.skill_evidence_engine import SkillEvidenceEngine
from prism.intelligence.skill_tracker import SkillTracker


@pytest.fixture
def evidence_engine() -> SkillEvidenceEngine:
    tracker = SkillTracker()
    return SkillEvidenceEngine(skill_tracker=tracker)


def test_process_activity_creates_skill_evidence(
    evidence_engine: SkillEvidenceEngine,
) -> None:
    now = datetime.now(UTC)
    activity = DeveloperActivity(
        event_id="act_py_1",
        developer_id="dev_alice",
        event_type="function_create",
        project_path="/projects/prism",
        file_path="src/api.py",
        timestamp=now,
        metadata={
            "classification": {
                "language": "Python",
                "framework": "FastAPI",
                "concept": "API Development",
                "related_skill": "FastAPI",
                "complexity_estimate": "high",
                "confidence_score": 0.95,
            }
        },
    )

    ev_list = evidence_engine.process_activity(activity)
    assert len(ev_list) >= 2  # Python + FastAPI

    skills_recorded = {e.skill_name for e in ev_list}
    assert "Python" in skills_recorded
    assert "FastAPI" in skills_recorded

    for ev in ev_list:
        assert ev.developer_id == "dev_alice"
        assert ev.evidence_strength == 1.1  # function_create weight
        assert ev.complexity_score == 1.0  # high complexity
        assert ev.confidence_score == 0.95
        assert ev.related_activity_id == "act_py_1"


def test_process_activity_ignores_trivial_events(
    evidence_engine: SkillEvidenceEngine,
) -> None:
    now = datetime.now(UTC)
    file_open_act = DeveloperActivity(
        event_id="act_open_1",
        developer_id="dev_bob",
        event_type="file_open",
        project_path="/projects/prism",
        file_path="main.py",
        timestamp=now,
    )
    ai_help_act = DeveloperActivity(
        event_id="act_ai_1",
        developer_id="dev_bob",
        event_type="ai_help",
        project_path="/projects/prism",
        file_path="main.py",
        timestamp=now,
    )

    assert evidence_engine.process_activity(file_open_act) == []
    assert evidence_engine.process_activity(ai_help_act) == []
    profile = evidence_engine.tracker.get_profile("dev_bob")
    assert len(profile.skills) == 0


def test_process_activity_deduplication(evidence_engine: SkillEvidenceEngine) -> None:
    now = datetime.now(UTC)
    activity = DeveloperActivity(
        event_id="act_dup_1",
        developer_id="dev_carol",
        event_type="file_edit",
        project_path="/projects/repo1",
        file_path="src/service.py",
        timestamp=now,
        metadata={
            "classification": {
                "language": "Python",
                "complexity_estimate": "medium",
            }
        },
    )

    first_run = evidence_engine.process_activity(activity)
    assert len(first_run) == 1
    assert first_run[0].skill_name == "Python"

    # Repeated identical activity on the same date should be discarded
    second_run = evidence_engine.process_activity(activity)
    assert len(second_run) == 0

    profile = evidence_engine.tracker.get_profile("dev_carol")
    assert profile.skills["python"].evidence_count == 1


def test_record_direct_evidence(evidence_engine: SkillEvidenceEngine) -> None:
    skill = evidence_engine.record_direct_evidence(
        developer_id="dev_dan",
        skill_name="Docker",
        description="Created production multi-stage Dockerfile",
        project_path="/infra/docker",
        evidence_type="implementation",
        evidence_strength=1.5,
        complexity_score=0.8,
    )

    assert skill.developer_id == "dev_dan"
    assert skill.skill_name == "Docker"
    assert skill.evidence_count == 1
    assert len(skill.evidence_list) == 1
    assert skill.evidence_list[0].evidence_strength == 1.5


def test_record_direct_evidence_validation_error(
    evidence_engine: SkillEvidenceEngine,
) -> None:
    with pytest.raises(ValueError, match="Developer ID and skill name cannot be empty"):
        evidence_engine.record_direct_evidence("", "Python", "desc")

    with pytest.raises(ValueError, match="Developer ID and skill name cannot be empty"):
        evidence_engine.record_direct_evidence("dev1", "  ", "desc")
