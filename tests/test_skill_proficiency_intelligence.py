from datetime import UTC, datetime

from prism.intelligence.models.skill_models import (
    ProficiencyLevel,
    SkillEvidence,
)
from prism.intelligence.skill_tracker import SkillTracker


def make_evidence(
    dev: str,
    skill: str,
    idx: int,
    ev_type: str = "implementation",
    project: str = "/repo1",
    language: str | None = "Python",
    framework: str | None = None,
    strength: float = 1.0,
    complexity: float = 0.5,
) -> SkillEvidence:
    return SkillEvidence(
        evidence_id=f"ev_{skill}_{idx}",
        developer_id=dev,
        skill_name=skill,
        skill_id=skill.lower().replace(" ", "_"),
        evidence_type=ev_type,
        description=f"Evidence artifact {idx} for {skill}",
        project_path=project,
        programming_language=language,
        framework=framework,
        evidence_strength=strength,
        confidence_score=0.9,
        complexity_score=complexity,
        timestamp=datetime.now(UTC),
    )


def test_insufficient_data_assessment() -> None:
    tracker = SkillTracker()
    dev = "dev_junior"

    tracker.record_evidence(make_evidence(dev, "Go", 1))
    skill = tracker.record_evidence(make_evidence(dev, "Go", 2))

    assert skill.proficiency_level == ProficiencyLevel.INSUFFICIENT_DATA
    assert not skill.has_sufficient_evidence
    assert skill.proficiency_score > 0
    assert "Insufficient evidence" in (skill.reasoning or "")


def test_elementary_proficiency_level() -> None:
    tracker = SkillTracker()
    dev = "dev_elementary"

    for i in range(1, 5):
        tracker.record_evidence(
            make_evidence(dev, "TypeScript", i, ev_type="code_artifact")
        )

    skill = tracker.assess_skill(dev, "TypeScript")
    assert skill.evidence_count == 4
    assert skill.proficiency_level == ProficiencyLevel.ELEMENTARY
    assert skill.has_sufficient_evidence
    assert "Elementary competence" in (skill.reasoning or "")


def test_expert_proficiency_level() -> None:
    tracker = SkillTracker()
    dev = "dev_expert"

    # 20+ pieces of evidence across 3 projects and diverse types with high complexity
    projects = ["/p1", "/p2", "/p3"]
    types = ["project_feature", "test_pass", "refactor"]

    for i in range(1, 24):
        proj = projects[i % 3]
        ev_type = types[i % 3]
        tracker.record_evidence(
            make_evidence(
                dev,
                "Python",
                i,
                ev_type=ev_type,
                project=proj,
                strength=1.5,
                complexity=1.0,
            )
        )

    skill = tracker.assess_skill(dev, "Python")
    assert skill.evidence_count == 23
    assert skill.proficiency_level == ProficiencyLevel.EXPERT
    assert skill.proficiency_score >= 80.0
    assert "Expert proficiency verified" in (skill.reasoning or "")


def test_inflation_prevention_on_repetitive_edits() -> None:
    tracker = SkillTracker()
    dev = "dev_spammer"

    # Developer has 10 trivial file edit activities in a single project with no test passes or features
    for i in range(1, 11):
        tracker.record_evidence(
            make_evidence(
                dev,
                "Java",
                i,
                ev_type="file_edit",
                project="/single_repo",
                strength=0.5,
                complexity=0.2,
            )
        )

    skill = tracker.assess_skill(dev, "Java")
    # Should not be intermediate or advanced because of lack of verified artifacts and multi-project diversity
    assert skill.proficiency_level in (
        ProficiencyLevel.ELEMENTARY,
        ProficiencyLevel.BEGINNER,
    )
    assert skill.proficiency_level != ProficiencyLevel.ADVANCED
    assert skill.proficiency_level != ProficiencyLevel.EXPERT


def test_developer_skill_profile_multidimensional_summary() -> None:
    tracker = SkillTracker()
    dev = "dev_fullstack"

    # Python (Intermediate)
    for i in range(1, 7):
        ev_type = "test_pass" if i == 6 else "implementation"
        tracker.record_evidence(
            make_evidence(
                dev,
                "Python",
                i,
                ev_type=ev_type,
                language="Python",
                framework=None,
            )
        )

    # FastAPI (Elementary)
    for i in range(1, 5):
        tracker.record_evidence(
            make_evidence(
                dev,
                "FastAPI",
                i,
                language="Python",
                framework="FastAPI",
            )
        )

    profile = tracker.get_profile(dev)
    assert profile.language_proficiency.get("Python") == "intermediate"
    assert profile.framework_proficiency.get("FastAPI") == "elementary"
    assert "FastAPI" in profile.weakest_skills
    assert profile.overall_proficiency in ("intermediate", "elementary")
