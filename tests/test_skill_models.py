from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    DeveloperSkillProfile,
    ProficiencyLevel,
    RelationshipType,
    SkillEvidence,
    SkillGraphData,
    SkillRelationship,
)


def test_skill_evidence_creation_and_extra_forbid() -> None:
    now = datetime.now(UTC)
    evidence = SkillEvidence(
        evidence_id="ev-1",
        developer_id="dev-1",
        skill_name="Python",
        evidence_type="code_artifact",
        description="Built clean code",
        timestamp=now,
        project_path="/proj",
    )
    assert evidence.skill_name == "Python"
    assert evidence.metadata == {}

    with pytest.raises(ValidationError):
        SkillEvidence(
            evidence_id="ev-1",
            developer_id="dev-1",
            skill_name="Python",
            evidence_type="code_artifact",
            description="Built clean code",
            timestamp=now,
            extra="bad",  # type: ignore[call-arg]
        )


def test_skill_relationship_model() -> None:
    rel = SkillRelationship(
        from_skill="Python",
        to_skill="FastAPI",
        relationship_type=RelationshipType.PREREQUISITE,
    )
    assert rel.from_skill == "Python"
    assert rel.to_skill == "FastAPI"
    assert rel.relationship_type == RelationshipType.PREREQUISITE


def test_developer_skill_model_and_getitem() -> None:
    skill = DeveloperSkill(
        developer_id="dev-1",
        skill_name="Python",
        proficiency_level=ProficiencyLevel.INTERMEDIATE,
        evidence_count=6,
        has_sufficient_evidence=True,
    )
    assert skill["skill_name"] == "Python"
    assert skill["proficiency_level"] == ProficiencyLevel.INTERMEDIATE
    assert skill["evidence_count"] == 6

    with pytest.raises(KeyError):
        _ = skill["missing_field"]


def test_developer_skill_profile_model() -> None:
    skill = DeveloperSkill(
        developer_id="dev-1",
        skill_name="Python",
    )
    profile = DeveloperSkillProfile(
        developer_id="dev-1",
        skills={"python": skill},
    )
    assert profile.get_skill("Python") == skill
    assert profile.get_skill("python") == skill
    assert profile.get_skill("Rust") is None
    assert profile["developer_id"] == "dev-1"


def test_skill_graph_data_model() -> None:
    data = SkillGraphData(
        skills=["Python", "NumPy"],
        relationships=[
            SkillRelationship(
                from_skill="Python",
                to_skill="NumPy",
                relationship_type=RelationshipType.PREREQUISITE,
            )
        ],
    )
    assert len(data.skills) == 2
    assert len(data.relationships) == 1
