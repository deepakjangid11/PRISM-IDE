from datetime import UTC, datetime

from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    DeveloperSkillProfile,
    ProficiencyLevel,
)
from prism.intelligence.skill_graph import SkillGraphBuilder
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.learning.learning_path_generator import LearningPathGenerator
from prism.learning.models import RecommendationPriority
from prism.learning.recommendation_engine import LearningRecommendationEngine


def make_profile(
    dev_id: str, skills_and_levels: dict[str, ProficiencyLevel]
) -> DeveloperSkillProfile:
    skills = {}
    for name, level in skills_and_levels.items():
        skills[name.lower()] = DeveloperSkill(
            developer_id=dev_id,
            skill_name=name,
            proficiency_level=level,
            evidence_count=6 if level == ProficiencyLevel.INTERMEDIATE else 3,
            has_sufficient_evidence=level != ProficiencyLevel.INSUFFICIENT_DATA,
            last_assessed=datetime.now(UTC),
        )
    return DeveloperSkillProfile(
        developer_id=dev_id,
        skills=skills,
        last_updated=datetime.now(UTC),
    )


def test_gap_analyzer_role_gaps() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    analyzer = KnowledgeGapAnalyzer(graph)

    # Developer has Python (Intermediate), but lacks NumPy and Machine Learning for ML Engineer
    profile = make_profile(
        "dev_ml_candidate", {"Python": ProficiencyLevel.INTERMEDIATE}
    )

    gaps = analyzer.identify_role_gaps(profile, "Machine Learning Engineer")
    gap_skills = {g.missing_skill for g in gaps}

    assert "NumPy" in gap_skills
    assert "Machine Learning" in gap_skills
    assert any(
        "prerequisite" in (g.importance_reason or "").lower()
        or "role" in (g.importance_reason or "").lower()
        for g in gaps
    )


def test_recommendation_engine_priorities_and_effort() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    analyzer = KnowledgeGapAnalyzer(graph)
    engine = LearningRecommendationEngine()

    profile = make_profile("dev_candidate", {"Python": ProficiencyLevel.INTERMEDIATE})
    gaps = analyzer.identify_role_gaps(profile, "Backend Developer")

    recs = engine.generate_recommendations(
        profile, gaps, target_role="Backend Developer"
    )
    assert len(recs) > 0

    for rec in recs:
        assert rec.priority_level in (
            RecommendationPriority.CRITICAL,
            RecommendationPriority.HIGH,
            RecommendationPriority.MEDIUM,
            RecommendationPriority.LOW,
        )
        assert rec.estimated_effort_hours > 0
        assert rec.target_proficiency != ""
        assert rec.reason != ""


def test_learning_path_role_generation() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    generator = LearningPathGenerator(graph)

    # Developer has Python and FastAPI
    profile = make_profile(
        "dev_be",
        {
            "Python": ProficiencyLevel.INTERMEDIATE,
            "FastAPI": ProficiencyLevel.INTERMEDIATE,
        },
    )

    path = generator.generate_role_path(profile, "Backend Developer")

    assert path.target_role == "Backend Developer"
    assert "Python" in path.completed_steps
    assert "FastAPI" in path.completed_steps
    assert "REST APIs" in path.steps
    assert path.estimated_effort_hours > 0
