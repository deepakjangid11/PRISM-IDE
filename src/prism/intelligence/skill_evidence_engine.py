import hashlib
import time
import uuid
from datetime import UTC, datetime

from prism.intelligence.models.developer_behavior_models import DeveloperActivity
from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    SkillEvidence,
)
from prism.intelligence.skill_tracker import SkillTracker
from prism.logging.logger import get_logger

logger = get_logger(__name__)


# Trivial events that do NOT constitute valid skill proficiency evidence
IGNORED_EVENT_TYPES = {"file_open", "ai_help"}

# Weights for event types
EVENT_STRENGTH_MAP: dict[str, float] = {
    "class_create": 1.2,
    "component_create": 1.2,
    "function_create": 1.1,
    "refactor": 1.3,
    "test_success": 1.1,
    "test_run": 0.8,
    "file_edit": 1.0,
    "file_modify": 1.0,
    "file_create": 1.0,
    "syntax_error": 0.3,
    "runtime_error": 0.4,
    "debug": 0.7,
}

COMPLEXITY_SCORE_MAP: dict[str, float] = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.3,
}


class SkillEvidenceEngine:
    """Engine responsible for extracting, validating, deduplicating, and scoring skill evidence."""

    def __init__(self, skill_tracker: SkillTracker | None = None) -> None:
        self.tracker = skill_tracker or SkillTracker()
        self._fingerprints: set[str] = set()

    def process_activity(self, activity: DeveloperActivity) -> list[SkillEvidence]:
        """Convert a developer activity into structured skill evidence records."""
        start_time = time.perf_counter()

        ev_type = activity.event_type.lower().strip()
        if ev_type in IGNORED_EVENT_TYPES:
            logger.debug(
                "Skipping non-evidential activity | event_type=%s | event_id=%s",
                ev_type,
                activity.event_id,
            )
            return []

        meta = activity.metadata or {}
        clf = meta.get("classification", {})

        language = clf.get("language") or meta.get("language")
        framework = clf.get("framework") or meta.get("framework")
        concept = clf.get("concept") or "General Programming"
        related_skill = clf.get("related_skill")
        complexity = clf.get("complexity_estimate", "medium")
        confidence = float(clf.get("confidence_score", 0.85))

        # Target skill names to record evidence for
        target_skills: set[str] = set()
        if related_skill:
            target_skills.add(related_skill)
        if language and language != "Unknown":
            target_skills.add(language)
        if framework:
            target_skills.add(framework)

        # In case none were specifically identified, record under concept
        if not target_skills and concept:
            target_skills.add(concept)

        evidence_strength = EVENT_STRENGTH_MAP.get(ev_type, 0.8)
        complexity_score = COMPLEXITY_SCORE_MAP.get(complexity, 0.6)

        results: list[SkillEvidence] = []
        now = activity.timestamp or datetime.now(UTC)

        for skill_name in sorted(target_skills):
            # Deduplication fingerprint: developer + skill + project + event_type + file + date
            date_str = now.strftime("%Y-%m-%d")
            raw_key = f"{activity.developer_id}|{skill_name}|{activity.project_path}|{ev_type}|{activity.file_path}|{date_str}"
            fingerprint = hashlib.sha256(raw_key.encode()).hexdigest()

            if fingerprint in self._fingerprints:
                logger.debug(
                    "Duplicate evidence discarded | dev=%s | skill=%s | fp=%s",
                    activity.developer_id,
                    skill_name,
                    fingerprint[:8],
                )
                continue

            self._fingerprints.add(fingerprint)

            evidence = SkillEvidence(
                evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
                developer_id=activity.developer_id,
                skill_name=skill_name,
                skill_id=skill_name.lower().replace(" ", "_"),
                project_path=activity.project_path,
                programming_language=language,
                framework=framework,
                evidence_source="activity_stream",
                evidence_type="implementation"
                if "test" not in ev_type
                else "test_execution",
                description=f"Observed '{ev_type}' activity for '{skill_name}' in '{activity.file_path or 'project'}'.",
                evidence_strength=evidence_strength,
                confidence_score=confidence,
                complexity_score=complexity_score,
                timestamp=now,
                related_activity_id=activity.event_id,
                metadata={
                    "fingerprint": fingerprint,
                    "concept": concept,
                    "complexity": complexity,
                },
            )

            self.tracker.record_evidence(evidence)
            results.append(evidence)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Skill evidence processing completed | dev=%s | count=%d | duration_ms=%.2f",
            activity.developer_id,
            len(results),
            duration_ms,
        )
        return results

    def record_direct_evidence(
        self,
        developer_id: str,
        skill_name: str,
        description: str,
        project_path: str | None = None,
        programming_language: str | None = None,
        framework: str | None = None,
        evidence_type: str = "implementation",
        evidence_strength: float = 1.0,
        confidence_score: float = 0.90,
        complexity_score: float = 0.60,
    ) -> DeveloperSkill:
        """Record explicit/direct verifiable evidence for a skill."""
        cleaned_dev = developer_id.strip()
        cleaned_skill = skill_name.strip()
        if not cleaned_dev or not cleaned_skill:
            raise ValueError("Developer ID and skill name cannot be empty")

        now = datetime.now(UTC)
        evidence = SkillEvidence(
            evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
            developer_id=cleaned_dev,
            skill_name=cleaned_skill,
            skill_id=cleaned_skill.lower().replace(" ", "_"),
            project_path=project_path,
            programming_language=programming_language,
            framework=framework,
            evidence_source="direct_assessment",
            evidence_type=evidence_type,
            description=description,
            evidence_strength=evidence_strength,
            confidence_score=confidence_score,
            complexity_score=complexity_score,
            timestamp=now,
        )
        return self.tracker.record_evidence(evidence)
