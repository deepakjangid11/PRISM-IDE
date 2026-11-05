from __future__ import annotations

import math
import sys
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from prism.storage.repositories.base import (
        DeveloperRepository,
        SkillRepository,
    )

logger = get_logger(__name__)

MINIMUM_EVIDENCE_FOR_ASSESSMENT = 3


class SkillTracker:
    """Tracks, stores, and evaluates evidence-based skill profiles for developers."""

    def __init__(
        self,
        repository: SkillRepository | None = None,
        developer_repo: DeveloperRepository | None = None,
    ) -> None:
        self._profiles: dict[str, DeveloperSkillProfile] = {}
        self._repository = repository
        self._dev_repo = developer_repo

    def get_profile(self, developer_id: str) -> DeveloperSkillProfile:
        """Retrieve or initialize the skill profile for a developer with multidimensional metrics."""
        dev_id = developer_id.strip()
        if not dev_id:
            raise ValueError("Developer ID cannot be empty")

        if dev_id not in self._profiles:
            if self._repository is not None:
                repo_profile = self._repository.get_profile(dev_id)
                if repo_profile.skills:
                    self._update_profile_summary(repo_profile)
                    self._profiles[dev_id] = repo_profile
                    return repo_profile

            profile = DeveloperSkillProfile(
                developer_id=dev_id,
                skills={},
                last_updated=datetime.now(UTC),
            )
            self._update_profile_summary(profile)
            self._profiles[dev_id] = profile

        profile = self._profiles[dev_id]
        self._update_profile_summary(profile)
        return profile

    def record_evidence(self, evidence: SkillEvidence) -> DeveloperSkill:
        """Record concrete evidence for a skill and re-evaluate proficiency with weighted scoring."""
        profile = self.get_profile(evidence.developer_id)
        skill_key = evidence.skill_name.strip().lower()
        canonical_name = evidence.skill_name.strip()

        if skill_key not in profile.skills:
            dev_skill = DeveloperSkill(
                developer_id=evidence.developer_id,
                skill_name=canonical_name,
                skill_id=evidence.skill_id or canonical_name.lower().replace(" ", "_"),
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
        self._update_profile_summary(profile)
        profile.last_updated = datetime.now(UTC)

        if self._repository is not None:
            self._repository.record_evidence(evidence)
            self._repository.save_skill_assessment(dev_skill)

        logger.info(
            "Recorded skill evidence | dev=%s | skill=%s | count=%d | level=%s | score=%.1f",
            evidence.developer_id,
            canonical_name,
            dev_skill.evidence_count,
            dev_skill.proficiency_level.value,
            dev_skill.proficiency_score,
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
            skill_id=skill_name.strip().lower().replace(" ", "_"),
            proficiency_level=ProficiencyLevel.INSUFFICIENT_DATA,
            proficiency_score=0.0,
            confidence=0.0,
            evidence_count=0,
            evidence_list=[],
            has_sufficient_evidence=False,
            last_assessed=None,
            reasoning=f"No verified development activity or evidence recorded for '{skill_name.strip()}'.",
        )

    def list_developers(self) -> list[str]:
        """Return list of all registered developer IDs."""
        dev_set = set(self._profiles.keys())
        if self._repository is not None:
            dev_set.update(self._repository.list_developers())
        return sorted(dev_set)

    @staticmethod
    def _evaluate_proficiency(skill: DeveloperSkill) -> None:
        """Evaluate evidence-based proficiency using diminishing returns and weighted scoring."""
        count = skill.evidence_count
        if count < MINIMUM_EVIDENCE_FOR_ASSESSMENT:
            skill.proficiency_level = ProficiencyLevel.INSUFFICIENT_DATA
            skill.has_sufficient_evidence = False
            skill.proficiency_score = round(count * 5.0, 1)
            skill.confidence = round(
                sum(e.confidence_score for e in skill.evidence_list) / max(1, count), 2
            )
            skill.reasoning = (
                f"Insufficient evidence ({count}/{MINIMUM_EVIDENCE_FOR_ASSESSMENT} data points) "
                "to form a reliable competency baseline."
            )
            return

        skill.has_sufficient_evidence = True
        evidence_types = {e.evidence_type for e in skill.evidence_list}
        projects = {e.project_path for e in skill.evidence_list if e.project_path}

        # 1. Quantity score with diminishing returns: max 30 points
        qty_score = min(30.0, 10.0 * math.log(1 + count))

        # 2. Quality & Strength score: max 25 points
        avg_strength = sum(e.evidence_strength for e in skill.evidence_list) / count
        strength_score = min(25.0, avg_strength * 20.0)

        # 3. Complexity score: max 20 points
        avg_complexity = sum(e.complexity_score for e in skill.evidence_list) / count
        complexity_score = min(20.0, avg_complexity * 20.0)

        # 4. Diversity score (projects & types): max 15 points
        diversity_score = min(15.0, (len(projects) * 4.0) + (len(evidence_types) * 3.5))

        # 5. Confidence score: max 10 points
        avg_conf = sum(e.confidence_score for e in skill.evidence_list) / count
        conf_score = avg_conf * 10.0

        total_score = round(
            qty_score
            + strength_score
            + complexity_score
            + diversity_score
            + conf_score,
            1,
        )
        skill.proficiency_score = min(100.0, total_score)
        skill.confidence = round(avg_conf, 2)

        # Level assignment ensuring backward-compatibility with baseline rules
        has_verified_artifact = (
            "test_pass" in evidence_types
            or "project_feature" in evidence_types
            or "test_execution" in evidence_types
            or "code_refactoring" in evidence_types
        )

        if (
            count >= 20
            and len(projects) >= 3
            and len(evidence_types) >= 3
            and total_score >= 80.0
        ):
            skill.proficiency_level = ProficiencyLevel.EXPERT
            skill.reasoning = (
                f"Expert proficiency verified across {len(projects)} distinct projects "
                f"with {count} activities and high implementation complexity."
            )
        elif count >= 12 and len(evidence_types) >= 2 and len(projects) >= 2:
            skill.proficiency_level = ProficiencyLevel.ADVANCED
            skill.reasoning = (
                f"Advanced competence established across multiple projects ({len(projects)}) "
                f"and diverse activity types with {count} verified data points."
            )
        elif count >= 6 and has_verified_artifact:
            skill.proficiency_level = ProficiencyLevel.INTERMEDIATE
            skill.reasoning = (
                f"Intermediate competence demonstrated with {count} activities "
                "including verified testing or production implementations."
            )
        elif count >= 4:
            skill.proficiency_level = ProficiencyLevel.ELEMENTARY
            skill.reasoning = (
                f"Elementary competence: {count} verified activities with basic "
                "practical implementation evidence established."
            )
        else:
            skill.proficiency_level = ProficiencyLevel.BEGINNER
            skill.reasoning = (
                f"Beginner baseline: {count} activities observed. "
                "Additional project features and tests required for intermediate rating."
            )

    @staticmethod
    def _update_profile_summary(profile: DeveloperSkillProfile) -> None:
        """Derive high-level summary distributions and highlights across developer skills."""
        if not profile.skills:
            return

        lang_map: dict[str, str] = {}
        fw_map: dict[str, str] = {}
        concept_map: dict[str, str] = {}

        strong: list[str] = []
        weak: list[str] = []
        insufficient: list[str] = []

        level_weights = {
            ProficiencyLevel.INSUFFICIENT_DATA: 0,
            ProficiencyLevel.BEGINNER: 1,
            ProficiencyLevel.ELEMENTARY: 2,
            ProficiencyLevel.INTERMEDIATE: 3,
            ProficiencyLevel.ADVANCED: 4,
            ProficiencyLevel.EXPERT: 5,
        }

        total_weight = 0
        assessed_count = 0

        for skill in profile.skills.values():
            name = skill.skill_name
            level = skill.proficiency_level

            # Extract language/framework metadata from latest evidence keeping highest proficiency
            for ev in reversed(skill.evidence_list):
                if ev.programming_language:
                    curr_val = lang_map.get(ev.programming_language)
                    if (
                        curr_val is None
                        or level_weights[level]
                        > level_weights[ProficiencyLevel(curr_val)]
                    ):
                        lang_map[ev.programming_language] = level.value
                if ev.framework:
                    curr_fw = fw_map.get(ev.framework)
                    if (
                        curr_fw is None
                        or level_weights[level]
                        > level_weights[ProficiencyLevel(curr_fw)]
                    ):
                        fw_map[ev.framework] = level.value

            if not skill.has_sufficient_evidence:
                insufficient.append(name)
            elif level in (ProficiencyLevel.ADVANCED, ProficiencyLevel.EXPERT):
                strong.append(name)
            elif level in (ProficiencyLevel.BEGINNER, ProficiencyLevel.ELEMENTARY):
                weak.append(name)

            if skill.has_sufficient_evidence:
                total_weight += level_weights[level]
                assessed_count += 1

        profile.language_proficiency = lang_map
        profile.framework_proficiency = fw_map
        profile.concept_proficiency = concept_map
        profile.strongest_skills = sorted(strong)
        profile.weakest_skills = sorted(weak)
        profile.insufficient_evidence_skills = sorted(insufficient)

        if assessed_count > 0:
            avg_weight = total_weight / assessed_count
            if avg_weight >= 4.0:
                profile.overall_proficiency = ProficiencyLevel.ADVANCED.value
            elif avg_weight >= 2.5:
                profile.overall_proficiency = ProficiencyLevel.INTERMEDIATE.value
            elif avg_weight >= 1.5:
                profile.overall_proficiency = ProficiencyLevel.ELEMENTARY.value
            else:
                profile.overall_proficiency = ProficiencyLevel.BEGINNER.value
        else:
            profile.overall_proficiency = ProficiencyLevel.INSUFFICIENT_DATA.value


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
                    skill_id="python",
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
                    skill_id="object-oriented_programming",
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
                        skill_id="fastapi",
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
                        skill_id="testing",
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
                        skill_id="data_validation",
                        evidence_type="code_artifact",
                        description=f"Used Pydantic data schemas in {dep.source_file}.",
                        timestamp=now,
                        project_path=proj_path,
                    )
                    self.tracker.record_evidence(ev)
                    extracted_evidence.append(ev)

            # 4. Software Architecture evidence
            if project_intelligence.code_relationships:
                rel_count = sum(
                    len(r.classes) + len(r.functions)
                    for r in project_intelligence.code_relationships
                )
                if rel_count > 0:
                    evidence = SkillEvidence(
                        evidence_id=str(uuid.uuid4()),
                        developer_id=developer_id,
                        skill_name="Software Architecture",
                        skill_id="software_architecture",
                        evidence_type="code_artifact",
                        description=(
                            f"Identified {rel_count} structured code relationships "
                            "across project components."
                        ),
                        timestamp=now,
                        project_path=proj_path,
                    )
                    self.tracker.record_evidence(evidence)
                    extracted_evidence.append(evidence)

            logger.info(
                "Extracted %d skill evidence items for developer '%s'",
                len(extracted_evidence),
                developer_id,
            )
            return extracted_evidence

        except Exception as error:
            logger.exception("Failed to analyze project skills")
            raise CustomException(error, sys) from error
