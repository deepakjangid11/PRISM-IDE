import uuid

from prism.intelligence.models.skill_models import (
    DeveloperSkillProfile,
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
        """Identify missing prerequisites and skills with insufficient evidence."""
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
                    description=(
                        f"Target skill '{cleaned_target}' has insufficient evidence "
                        f"({target_dev_skill.evidence_count} evidence items)."
                    ),
                    severity="medium",
                )
            )

        logger.info(
            "Identified %d knowledge gaps for '%s'",
            len(gaps),
            cleaned_target,
        )
        return gaps
