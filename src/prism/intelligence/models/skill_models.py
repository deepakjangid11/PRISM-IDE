from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProficiencyLevel(StrEnum):
    """Proficiency levels grounded in verifiable evidence."""

    INSUFFICIENT_DATA = "insufficient_data"
    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class RelationshipType(StrEnum):
    """Types of relationships between technical skills and concepts."""

    PREREQUISITE = "prerequisite"
    DEPENDENCY = "dependency"
    RELATED = "related"
    SPECIALIZATION_OF = "specialization_of"
    FRAMEWORK_OF = "framework_of"
    LANGUAGE_OF = "language_of"


class SkillNode(BaseModel):
    """Metadata node in the technical skill and concept graph."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str
    name: str
    category: str = "general"
    language: str | None = None
    difficulty: str = "intermediate"
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class SkillEvidence(BaseModel):
    """Verifiable concrete evidence supporting technical skill proficiency."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    developer_id: str
    skill_name: str
    skill_id: str | None = None
    project_path: str | None = None
    programming_language: str | None = None
    framework: str | None = None
    evidence_source: str = "code_artifact"
    evidence_type: str = "implementation"
    description: str
    evidence_strength: float = 1.0
    confidence_score: float = 0.85
    complexity_score: float = 0.5
    timestamp: datetime
    related_activity_id: str | None = None
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
    skill_id: str | None = None
    proficiency_level: ProficiencyLevel = ProficiencyLevel.INSUFFICIENT_DATA
    proficiency_score: float = 0.0
    confidence: float = 0.0
    evidence_count: int = 0
    evidence_list: list[SkillEvidence] = Field(default_factory=list)
    has_sufficient_evidence: bool = False
    last_assessed: datetime | None = None
    reasoning: str | None = None

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
    overall_proficiency: str = ProficiencyLevel.BEGINNER.value
    language_proficiency: dict[str, str] = Field(default_factory=dict)
    framework_proficiency: dict[str, str] = Field(default_factory=dict)
    concept_proficiency: dict[str, str] = Field(default_factory=dict)
    strongest_skills: list[str] = Field(default_factory=list)
    weakest_skills: list[str] = Field(default_factory=list)
    insufficient_evidence_skills: list[str] = Field(default_factory=list)

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
    nodes: list[SkillNode] = Field(default_factory=list)
    relationships: list[SkillRelationship] = Field(default_factory=list)
