import pytest

from prism.intelligence.models.skill_models import RelationshipType
from prism.intelligence.skill_graph import SkillGraph, SkillGraphBuilder


def test_skill_graph_add_and_query_prerequisites() -> None:
    graph = SkillGraph()
    graph.add_relationship("Python", "NumPy", RelationshipType.PREREQUISITE)
    graph.add_relationship("NumPy", "Pandas", RelationshipType.PREREQUISITE)
    graph.add_relationship("Pandas", "Machine Learning", RelationshipType.PREREQUISITE)

    # Direct prerequisites of Pandas
    direct = graph.get_prerequisites("Pandas", transitive=False)
    assert direct == ["NumPy"]

    # Transitive prerequisites of Machine Learning (topological order: Python, NumPy, Pandas)
    transitive = graph.get_prerequisites("Machine Learning", transitive=True)
    assert transitive == ["Python", "NumPy", "Pandas"]


def test_skill_graph_detects_and_prevents_cycles() -> None:
    graph = SkillGraph()
    graph.add_relationship("SkillA", "SkillB", RelationshipType.PREREQUISITE)
    graph.add_relationship("SkillB", "SkillC", RelationshipType.PREREQUISITE)

    # Attempt to add SkillC -> SkillA (creates cycle)
    with pytest.raises(ValueError, match="Circular prerequisite detected"):
        graph.add_relationship("SkillC", "SkillA", RelationshipType.PREREQUISITE)


def test_skill_graph_self_relationship_rejected() -> None:
    graph = SkillGraph()
    with pytest.raises(ValueError, match="cannot have a relationship with itself"):
        graph.add_relationship("Python", "python")


def test_skill_graph_empty_skill_rejected() -> None:
    graph = SkillGraph()
    with pytest.raises(ValueError, match="cannot be empty"):
        graph.add_skill("   ")


def test_skill_graph_dependents_and_related() -> None:
    graph = SkillGraph()
    graph.add_relationship("Python", "FastAPI", RelationshipType.PREREQUISITE)
    graph.add_relationship("FastAPI", "REST APIs", RelationshipType.RELATED)

    assert graph.get_dependents("Python") == ["FastAPI"]
    assert "REST APIs" in graph.get_related_skills("FastAPI")
    assert "FastAPI" in graph.get_related_skills("REST APIs")


def test_default_skill_graph_builder() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    assert graph.has_skill("Python")
    assert graph.has_skill("Machine Learning")
    assert graph.has_skill("FastAPI")

    # Prereqs for Machine Learning
    ml_prereqs = graph.get_prerequisites("Machine Learning")
    assert "Python" in ml_prereqs
    assert "NumPy" in ml_prereqs
    assert "Pandas" in ml_prereqs

    export_data = graph.export_graph()
    assert len(export_data.skills) > 10
    assert len(export_data.relationships) > 5
