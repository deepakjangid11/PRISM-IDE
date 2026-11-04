from datetime import UTC, datetime

import pytest

from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    DeveloperSkillProfile,
    ProficiencyLevel,
    SkillEvidence,
)
from prism.intelligence.skill_graph import SkillGraphBuilder
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.learning_path_generator import LearningPathGenerator
from prism.learning.models import KnowledgeGapType
from prism.learning.progress_tracker import LearningProgressTracker
from prism.learning.recommendation_engine import LearningRecommendationEngine


def make_profile_with_skills(
    dev_id: str, skills_evidence_counts: dict[str, int]
) -> DeveloperSkillProfile:
    profile = DeveloperSkillProfile(
        developer_id=dev_id, skills={}, last_updated=datetime.now(UTC)
    )
    for skill_name, count in skills_evidence_counts.items():
        evidence_list = [
            SkillEvidence(
                evidence_id=f"ev-{skill_name}-{i}",
                developer_id=dev_id,
                skill_name=skill_name,
                evidence_type="code_artifact",
                description=f"Artifact {i}",
                timestamp=datetime.now(UTC),
            )
            for i in range(count)
        ]
        has_sufficient = count >= 3
        level = (
            ProficiencyLevel.INTERMEDIATE
            if count >= 6
            else (
                ProficiencyLevel.BEGINNER
                if count >= 3
                else ProficiencyLevel.INSUFFICIENT_DATA
            )
        )
        profile.skills[skill_name.lower()] = DeveloperSkill(
            developer_id=dev_id,
            skill_name=skill_name,
            proficiency_level=level,
            evidence_count=count,
            evidence_list=evidence_list,
            has_sufficient_evidence=has_sufficient,
            last_assessed=datetime.now(UTC),
        )
    return profile


def test_gap_analyzer_detects_all_missing_prerequisites() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    analyzer = KnowledgeGapAnalyzer(graph)

    # Empty profile: target Machine Learning
    profile = make_profile_with_skills("dev_novice", {})
    gaps = analyzer.identify_gaps(profile, "Machine Learning")

    missing_skills = {g.missing_skill for g in gaps}
    assert "Python" in missing_skills
    assert "NumPy" in missing_skills
    assert "Pandas" in missing_skills
    assert "Statistics" in missing_skills
    assert "Machine Learning" in missing_skills


def test_gap_analyzer_distinguishes_insufficient_evidence() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    analyzer = KnowledgeGapAnalyzer(graph)

    # Python has 1 piece of evidence (< 3)
    profile = make_profile_with_skills("dev_partial", {"Python": 1})
    gaps = analyzer.identify_gaps(profile, "FastAPI")

    python_gaps = [g for g in gaps if g.missing_skill == "Python"]
    assert len(python_gaps) == 1
    assert python_gaps[0].gap_type == KnowledgeGapType.INSUFFICIENT_EVIDENCE


def test_gap_analyzer_empty_target_raises_value_error() -> None:
    analyzer = KnowledgeGapAnalyzer()
    profile = make_profile_with_skills("dev1", {})
    with pytest.raises(ValueError, match="Target skill must be non-empty"):
        analyzer.identify_gaps(profile, "   ")


def test_recommendation_engine_prioritization_and_deduplication() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    analyzer = KnowledgeGapAnalyzer(graph)
    engine = LearningRecommendationEngine()

    profile = make_profile_with_skills("dev1", {"Python": 4})
    gaps = analyzer.identify_gaps(profile, "Machine Learning")
    recs = engine.generate_recommendations(profile, gaps)

    # Verify priorities are sequential 1, 2, 3...
    priorities = [r.priority for r in recs]
    assert priorities == list(range(1, len(recs) + 1))

    # Verify no duplicate skills recommended
    skill_names = [r.skill_name.lower() for r in recs]
    assert len(skill_names) == len(set(skill_names))


def test_learning_path_generator_topological_ordering() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    generator = LearningPathGenerator(graph)

    profile = make_profile_with_skills("dev_learner", {})
    path = generator.generate_path(profile, "Machine Learning")

    # In Machine Learning pathway: Python must come before NumPy, NumPy before Pandas, Pandas before ML
    steps = path.steps
    assert "Python" in steps
    assert "NumPy" in steps
    assert "Pandas" in steps
    assert "Machine Learning" in steps

    assert steps.index("Python") < steps.index("NumPy")
    assert steps.index("NumPy") < steps.index("Pandas")
    assert steps.index("Pandas") < steps.index("Machine Learning")


def test_learning_path_skips_already_mastered_prerequisites() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    generator = LearningPathGenerator(graph)

    # Already has Python (5 evidence) and FastAPI (4 evidence)
    profile = make_profile_with_skills("dev_backend", {"Python": 5, "FastAPI": 4})
    path = generator.generate_path(profile, "REST APIs")

    assert "Python" not in path.steps
    assert "FastAPI" not in path.steps
    assert "REST APIs" in path.steps


def test_learning_progress_tracker() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    generator = LearningPathGenerator(graph)
    tracker = LearningProgressTracker()

    # Learning path for FastAPI: steps are Python, FastAPI
    path_profile = make_profile_with_skills("dev1", {})
    path = generator.generate_path(path_profile, "FastAPI")

    # Now developer has mastered Python, working on FastAPI
    active_profile = make_profile_with_skills("dev1", {"Python": 4, "FastAPI": 1})
    progress = tracker.track_progress(active_profile, path)

    assert "Python" in progress.completed_skills
    assert "FastAPI" in progress.in_progress_skills
    assert progress.completion_percentage == 50.0
