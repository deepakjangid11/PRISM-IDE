from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProficiencyLevel(StrEnum):
    """Proficiency levels grounded in verifiable evidence."""

    INSUFFICIENT_DATA = "insufficient_data"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class RelationshipType(StrEnum):
    """Types of relationships between technical skills."""

    PREREQUISITE = "prerequisite"
    RELATED = "related"
    SPECIALIZATION_OF = "specialization_of"


class SkillEvidence(BaseModel):
    """Verifiable concrete evidence supporting technical skill proficiency."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    developer_id: str
    skill_name: str
    evidence_type: str
    description: str
    timestamp: datetime
    project_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillRelationship(BaseModel):
    """Directional relationship between two skills in the skill graph."""

    model_config = ConfigDict(extra="forbid")

    from_skill: str
    to_skill: str
    relationship_type: RelationshipType = RelationshipType.PREREQUISITE


class DeveloperSkill(BaseModel):
    """A developer's competence in a specific skill based on accumulated evidence."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    skill_name: str
    proficiency_level: ProficiencyLevel = ProficiencyLevel.INSUFFICIENT_DATA
    evidence_count: int = 0
    evidence_list: list[SkillEvidence] = Field(default_factory=list)
    has_sufficient_evidence: bool = False
    last_assessed: datetime | None = None

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class DeveloperSkillProfile(BaseModel):
    """Collection of skills and proficiencies for a developer."""

    model_config = ConfigDict(extra="forbid")

    developer_id: str
    skills: dict[str, DeveloperSkill] = Field(default_factory=dict)
    last_updated: datetime | None = None

    def get_skill(self, skill_name: str) -> DeveloperSkill | None:
        return self.skills.get(skill_name.lower())

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as error:
            raise KeyError(item) from error


class SkillGraphData(BaseModel):
    """Serializable snapshot of the technical skill graph."""

    model_config = ConfigDict(extra="forbid")

    skills: list[str] = Field(default_factory=list)
    relationships: list[SkillRelationship] = Field(default_factory=list)
