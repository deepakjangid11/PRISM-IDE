import sys
import uuid
from datetime import UTC, datetime

from prism.exceptions.custom_exception import CustomException
from prism.intelligence.models.project_intelligence_models import (
    ProjectIntelligence,
)
from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    DeveloperSkillProfile,
    ProficiencyLevel,
    SkillEvidence,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)

MINIMUM_EVIDENCE_FOR_ASSESSMENT = 3


class SkillTracker:
    """Tracks, stores, and evaluates evidence-based skill profiles for developers."""

    def __init__(self) -> None:
        self._profiles: dict[str, DeveloperSkillProfile] = {}

    def get_profile(self, developer_id: str) -> DeveloperSkillProfile:
        """Retrieve or initialize the skill profile for a developer."""
        dev_id = developer_id.strip()
        if not dev_id:
            raise ValueError("Developer ID cannot be empty")

        if dev_id not in self._profiles:
            self._profiles[dev_id] = DeveloperSkillProfile(
                developer_id=dev_id,
                skills={},
                last_updated=datetime.now(UTC),
            )
        return self._profiles[dev_id]

    def record_evidence(self, evidence: SkillEvidence) -> DeveloperSkill:
        """Record concrete evidence for a skill and re-evaluate proficiency."""
        profile = self.get_profile(evidence.developer_id)
        skill_key = evidence.skill_name.strip().lower()
        canonical_name = evidence.skill_name.strip()

        if skill_key not in profile.skills:
            dev_skill = DeveloperSkill(
                developer_id=evidence.developer_id,
                skill_name=canonical_name,
                proficiency_level=ProficiencyLevel.INSUFFICIENT_DATA,
                evidence_count=0,
                evidence_list=[],
                has_sufficient_evidence=False,
                last_assessed=datetime.now(UTC),
            )
            profile.skills[skill_key] = dev_skill
        else:
            dev_skill = profile.skills[skill_key]

        dev_skill.evidence_list.append(evidence)
        dev_skill.evidence_count = len(dev_skill.evidence_list)
        dev_skill.last_assessed = datetime.now(UTC)

        self._evaluate_proficiency(dev_skill)
        profile.last_updated = datetime.now(UTC)

        logger.info(
            "Recorded skill evidence | dev=%s | skill=%s | count=%d | level=%s",
            evidence.developer_id,
            canonical_name,
            dev_skill.evidence_count,
            dev_skill.proficiency_level.value,
        )

        return dev_skill

    def assess_skill(self, developer_id: str, skill_name: str) -> DeveloperSkill:
        """Return the current evaluated skill assessment for a developer."""
        profile = self.get_profile(developer_id)
        skill_key = skill_name.strip().lower()
        if skill_key in profile.skills:
            return profile.skills[skill_key]

        return DeveloperSkill(
            developer_id=developer_id,
            skill_name=skill_name.strip(),
            proficiency_level=ProficiencyLevel.INSUFFICIENT_DATA,
            evidence_count=0,
            evidence_list=[],
            has_sufficient_evidence=False,
            last_assessed=None,
        )

    def list_developers(self) -> list[str]:
        """Return list of all registered developer IDs."""
        return sorted(self._profiles.keys())

    @staticmethod
    def _evaluate_proficiency(skill: DeveloperSkill) -> None:
        """Deterministically determine proficiency based on verified evidence count and types."""
        count = skill.evidence_count
        if count < MINIMUM_EVIDENCE_FOR_ASSESSMENT:
            skill.proficiency_level = ProficiencyLevel.INSUFFICIENT_DATA
            skill.has_sufficient_evidence = False
            return

        skill.has_sufficient_evidence = True
        evidence_types = {e.evidence_type for e in skill.evidence_list}
        projects = {e.project_path for e in skill.evidence_list if e.project_path}

        if count >= 12 and len(evidence_types) >= 2 and len(projects) >= 2:
            skill.proficiency_level = ProficiencyLevel.ADVANCED
        elif count >= 6 and (
            "test_pass" in evidence_types or "project_feature" in evidence_types
        ):
            skill.proficiency_level = ProficiencyLevel.INTERMEDIATE
        else:
            skill.proficiency_level = ProficiencyLevel.BEGINNER


class SkillAnalyzer:
    """Extract verifiable technical skill evidence from project intelligence."""

    def __init__(self, tracker: SkillTracker | None = None) -> None:
        self.tracker = tracker or SkillTracker()

    def analyze_project_skills(
        self,
        developer_id: str,
        project_intelligence: ProjectIntelligence,
    ) -> list[SkillEvidence]:
        """Extract concrete skill evidence from project intelligence artifacts."""
        try:
            extracted_evidence: list[SkillEvidence] = []
            proj_path = project_intelligence.project_path
            now = datetime.now(UTC)

            # 1. Python programming evidence
            if project_intelligence.summary.python_files_analyzed > 0:
                evidence = SkillEvidence(
                    evidence_id=str(uuid.uuid4()),
                    developer_id=developer_id,
                    skill_name="Python",
                    evidence_type="code_artifact",
                    description=(
                        f"Analyzed {project_intelligence.summary.python_files_analyzed} "
                        "Python source files in project."
                    ),
                    timestamp=now,
                    project_path=proj_path,
                )
                self.tracker.record_evidence(evidence)
                extracted_evidence.append(evidence)

            # 2. Object-Oriented Programming evidence
            if project_intelligence.summary.total_classes > 0:
                evidence = SkillEvidence(
                    evidence_id=str(uuid.uuid4()),
                    developer_id=developer_id,
                    skill_name="Object-Oriented Programming",
                    evidence_type="code_artifact",
                    description=(
                        f"Defined {project_intelligence.summary.total_classes} classes in project."
                    ),
                    timestamp=now,
                    project_path=proj_path,
                )
                self.tracker.record_evidence(evidence)
                extracted_evidence.append(evidence)

            # 3. Framework & Library dependencies
            for dep in project_intelligence.dependencies.dependencies:
                pkg = dep.imported_module.lower()
                if "fastapi" in pkg:
                    ev = SkillEvidence(
                        evidence_id=str(uuid.uuid4()),
                        developer_id=developer_id,
                        skill_name="FastAPI",
                        evidence_type="code_artifact",
                        description=f"Used FastAPI framework in {dep.source_file}.",
                        timestamp=now,
                        project_path=proj_path,
                    )
                    self.tracker.record_evidence(ev)
                    extracted_evidence.append(ev)

                elif "pytest" in pkg:
                    ev = SkillEvidence(
                        evidence_id=str(uuid.uuid4()),
                        developer_id=developer_id,
                        skill_name="Testing",
                        evidence_type="code_artifact",
                        description=f"Integrated automated testing in {dep.source_file}.",
                        timestamp=now,
                        project_path=proj_path,
                    )
                    self.tracker.record_evidence(ev)
                    extracted_evidence.append(ev)

                elif "pydantic" in pkg:
                    ev = SkillEvidence(
                        evidence_id=str(uuid.uuid4()),
                        developer_id=developer_id,
                        skill_name="Data Validation",
                        evidence_type="code_artifact",
                        description=f"Used Pydantic data schemas in {dep.source_file}.",
                        timestamp=now,
                        project_path=proj_path,
                    )
                    self.tracker.record_evidence(ev)
                    extracted_evidence.append(ev)

            return extracted_evidence

        except Exception as error:
            logger.error("Failed extracting skill evidence from project: %s", error)
            raise CustomException(error, sys) from error
