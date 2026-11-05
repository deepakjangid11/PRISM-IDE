import uuid

from prism.intelligence.models.skill_models import (
    DeveloperSkillProfile,
    ProficiencyLevel,
)
from prism.intelligence.skill_graph import SkillGraph, SkillGraphBuilder
from prism.learning.models import KnowledgeGap, KnowledgeGapType
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class KnowledgeGapAnalyzer:
    """Analyze developer profiles against skill graphs to detect knowledge gaps."""

    def __init__(self, skill_graph: SkillGraph | None = None) -> None:
        self.skill_graph = skill_graph or SkillGraphBuilder.build_default_graph()

    def identify_gaps(
        self,
        developer_profile: DeveloperSkillProfile,
        target_skill: str,
    ) -> list[KnowledgeGap]:
        """Identify missing prerequisites, weak concepts, and insufficient evidence for a target skill."""
        cleaned_target = target_skill.strip()
        if not cleaned_target:
            raise ValueError("Target skill must be non-empty")

        dev_id = developer_profile.developer_id
        gaps: list[KnowledgeGap] = []

        logger.info(
            "Analyzing knowledge gaps | dev=%s | target=%s",
            dev_id,
            cleaned_target,
        )

        direct_prereqs = set(
            self.skill_graph.get_prerequisites(cleaned_target, transitive=False)
        )
        transitive_prereqs = self.skill_graph.get_prerequisites(
            cleaned_target, transitive=True
        )

        # 1. Analyze prerequisites in dependency order
        for prereq in transitive_prereqs:
            dev_skill = developer_profile.get_skill(prereq)
            severity = "high" if prereq in direct_prereqs else "medium"

            if dev_skill is None:
                gaps.append(
                    KnowledgeGap(
                        gap_id=str(uuid.uuid4()),
                        developer_id=dev_id,
                        target_skill=cleaned_target,
                        missing_skill=prereq,
                        gap_type=KnowledgeGapType.MISSING_PREREQUISITE,
                        description=(
                            f"Missing required prerequisite '{prereq}' "
                            f"for mastering '{cleaned_target}'."
                        ),
                        severity=severity,
                        importance_reason=f"Foundational requirement: '{cleaned_target}' directly or transitively depends on '{prereq}'.",
                    )
                )
            elif not dev_skill.has_sufficient_evidence:
                gaps.append(
                    KnowledgeGap(
                        gap_id=str(uuid.uuid4()),
                        developer_id=dev_id,
                        target_skill=cleaned_target,
                        missing_skill=prereq,
                        gap_type=KnowledgeGapType.INSUFFICIENT_EVIDENCE,
                        description=(
                            f"Insufficient evidence for prerequisite '{prereq}'. "
                            f"Current level: {dev_skill.proficiency_level.value}."
                        ),
                        severity=severity,
                        importance_reason=f"Need additional verifiable code artifacts or test cases demonstrating competence in '{prereq}'.",
                    )
                )
            elif dev_skill.proficiency_level in (
                ProficiencyLevel.BEGINNER,
                ProficiencyLevel.ELEMENTARY,
            ):
                gaps.append(
                    KnowledgeGap(
                        gap_id=str(uuid.uuid4()),
                        developer_id=dev_id,
                        target_skill=cleaned_target,
                        missing_skill=prereq,
                        gap_type=KnowledgeGapType.LOW_PROFICIENCY,
                        description=(
                            f"Weak competency in prerequisite '{prereq}' "
                            f"(current: {dev_skill.proficiency_level.value})."
                        ),
                        severity=severity,
                        importance_reason=f"Advanced topics in '{cleaned_target}' require intermediate fluency in '{prereq}'.",
                    )
                )

        # 2. Check target skill itself
        target_dev_skill = developer_profile.get_skill(cleaned_target)
        if target_dev_skill is None:
            gaps.append(
                KnowledgeGap(
                    gap_id=str(uuid.uuid4()),
                    developer_id=dev_id,
                    target_skill=cleaned_target,
                    missing_skill=cleaned_target,
                    gap_type=KnowledgeGapType.MISSING_PREREQUISITE,
                    description=f"No prior experience or evidence recorded for '{cleaned_target}'.",
                    severity="high",
                    importance_reason="Target goal has not yet been started.",
                )
            )
        elif not target_dev_skill.has_sufficient_evidence:
            gaps.append(
                KnowledgeGap(
                    gap_id=str(uuid.uuid4()),
                    developer_id=dev_id,
                    target_skill=cleaned_target,
                    missing_skill=cleaned_target,
                    gap_type=KnowledgeGapType.INSUFFICIENT_EVIDENCE,
                    description=f"Initial evidence for '{cleaned_target}' is insufficient for mastery.",
                    severity="high",
                    importance_reason="Target goal requires practical project features and test validation.",
                )
            )

        return gaps

    def identify_role_gaps(
        self,
        developer_profile: DeveloperSkillProfile,
        target_role: str,
    ) -> list[KnowledgeGap]:
        """Analyze developer competencies against all skills required for a career role."""
        cleaned_role = target_role.strip()
        if not cleaned_role:
            raise ValueError("Target role must be non-empty")

        required_skills = self.skill_graph.get_role_skills(cleaned_role)
        if not required_skills:
            raise ValueError(f"Unknown career role: '{cleaned_role}'")

        all_gaps: list[KnowledgeGap] = []
        seen_skills: set[str] = set()

        for skill in required_skills:
            skill_gaps = self.identify_gaps(developer_profile, skill)
            for g in skill_gaps:
                if g.missing_skill.lower() not in seen_skills:
                    seen_skills.add(g.missing_skill.lower())
                    g.importance_reason = (
                        f"Required for role '{cleaned_role}' (supports '{skill}')."
                    )
                    all_gaps.append(g)

        return all_gaps
