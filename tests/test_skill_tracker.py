from datetime import UTC, datetime

import pytest

from prism.intelligence.models.dependency_models import (
    Dependency,
    DependencyAnalysis,
)
from prism.intelligence.models.project_intelligence_models import (
    ProjectContext,
    ProjectIntelligence,
    ProjectIntelligenceSummary,
)
from prism.intelligence.models.relationship_models import (
    ClassRelationship,
    CodeRelationshipAnalysis,
)
from prism.intelligence.models.skill_models import (
    ProficiencyLevel,
    SkillEvidence,
)
from prism.intelligence.skill_tracker import SkillAnalyzer, SkillTracker


def make_evidence(
    dev_id: str,
    skill: str,
    idx: int,
    ev_type: str = "code_artifact",
    project: str = "/p1",
) -> SkillEvidence:
    return SkillEvidence(
        evidence_id=f"ev-{idx}",
        developer_id=dev_id,
        skill_name=skill,
        evidence_type=ev_type,
        description=f"Evidence {idx}",
        timestamp=datetime.now(UTC),
        project_path=project,
    )


def test_skill_tracker_records_evidence_and_evaluates_levels() -> None:
    tracker = SkillTracker()
    dev = "dev_progression"

    # 1-2 pieces of evidence -> Insufficient Data
    tracker.record_evidence(make_evidence(dev, "Python", 1))
    skill = tracker.record_evidence(make_evidence(dev, "Python", 2))
    assert skill.evidence_count == 2
    assert skill.proficiency_level == ProficiencyLevel.INSUFFICIENT_DATA
    assert not skill.has_sufficient_evidence

    # 3 pieces of evidence -> Beginner
    skill = tracker.record_evidence(make_evidence(dev, "Python", 3))
    assert skill.evidence_count == 3
    assert skill.proficiency_level == ProficiencyLevel.BEGINNER
    assert skill.has_sufficient_evidence

    # 6 pieces with test_pass -> Intermediate
    for i in range(4, 6):
        tracker.record_evidence(make_evidence(dev, "Python", i))
    skill = tracker.record_evidence(
        make_evidence(dev, "Python", 6, ev_type="test_pass")
    )
    assert skill.evidence_count == 6
    assert skill.proficiency_level == ProficiencyLevel.INTERMEDIATE

    # 12 pieces across multiple projects and types -> Advanced
    for i in range(7, 12):
        tracker.record_evidence(
            make_evidence(dev, "Python", i, ev_type="code_artifact", project="/p1")
        )
    skill = tracker.record_evidence(
        make_evidence(dev, "Python", 12, ev_type="project_feature", project="/p2")
    )
    assert skill.evidence_count == 12
    assert skill.proficiency_level == ProficiencyLevel.ADVANCED


def test_assess_skill_returns_insufficient_for_unknown_skill() -> None:
    tracker = SkillTracker()
    assessment = tracker.assess_skill("dev_unknown", "Rust")
    assert assessment.skill_name == "Rust"
    assert assessment.proficiency_level == ProficiencyLevel.INSUFFICIENT_DATA
    assert not assessment.has_sufficient_evidence


def test_multiple_developers_tracked_independently() -> None:
    tracker = SkillTracker()
    tracker.record_evidence(make_evidence("alice", "Python", 1))
    tracker.record_evidence(make_evidence("bob", "SQL", 1))

    assert tracker.list_developers() == ["alice", "bob"]
    assert tracker.get_profile("alice").get_skill("python") is not None
    assert tracker.get_profile("bob").get_skill("sql") is not None
    assert tracker.get_profile("bob").get_skill("python") is None


def test_empty_developer_id_raises_value_error() -> None:
    tracker = SkillTracker()
    with pytest.raises(ValueError, match="Developer ID cannot be empty"):
        tracker.get_profile("   ")


def test_skill_analyzer_extracts_evidence_from_project_intelligence() -> None:
    summary = ProjectIntelligenceSummary(
        total_files=5,
        python_files_analyzed=5,
        total_classes=2,
        total_functions=4,
        total_function_calls=5,
        total_dependencies=2,
        local_dependencies=0,
        external_dependencies=2,
    )
    context = ProjectContext(
        project_path="/sample/project",
        total_files_discovered=5,
        python_files_analyzed=5,
        files=[],
        failed_files=[],
    )
    relationships = [
        CodeRelationshipAnalysis(
            file_path="src/models.py",
            classes=[
                ClassRelationship(
                    name="SubClass",
                    line=10,
                    bases=["BaseClass"],
                )
            ],
            functions=[],
            function_calls=[],
        )
    ]
    dependencies = DependencyAnalysis(
        project_path="/sample/project",
        total_python_files=5,
        total_dependencies=2,
        local_dependencies=0,
        external_dependencies=2,
        dependencies=[
            Dependency(
                source_file="api/main.py",
                imported_module="fastapi",
                is_local=False,
                line=1,
            ),
            Dependency(
                source_file="tests/test_all.py",
                imported_module="pytest",
                is_local=False,
                line=1,
            ),
        ],
        failed_files=[],
    )
    intelligence = ProjectIntelligence(
        project_path="/sample/project",
        project_context=context,
        dependencies=dependencies,
        code_relationships=relationships,
        summary=summary,
    )

    analyzer = SkillAnalyzer()
    evidence_list = analyzer.analyze_project_skills("dev_ai", intelligence)

    skill_names = {e.skill_name for e in evidence_list}
    assert "Python" in skill_names
    assert "Object-Oriented Programming" in skill_names
    assert "FastAPI" in skill_names
    assert "Testing" in skill_names

    profile = analyzer.tracker.get_profile("dev_ai")
    assert profile.get_skill("Python") is not None
    assert profile.get_skill("FastAPI") is not None
