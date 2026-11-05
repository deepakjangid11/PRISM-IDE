import pytest

from prism.intelligence.models.skill_models import (
    RelationshipType,
    SkillNode,
)
from prism.intelligence.skill_graph import SkillGraph, SkillGraphBuilder


def test_skill_graph_rich_nodes() -> None:
    graph = SkillGraph()
    node = SkillNode(
        skill_id="node_fastapi",
        name="FastAPI",
        category="framework",
        language="Python",
        difficulty="intermediate",
        description="Modern, fast web framework for building APIs with Python.",
        tags=["web", "api", "async"],
    )
    graph.add_node(node)

    retrieved = graph.get_node("fastapi")
    assert retrieved is not None
    assert retrieved.skill_id == "node_fastapi"
    assert retrieved.name == "FastAPI"
    assert retrieved.category == "framework"
    assert retrieved.language == "Python"
    assert retrieved.tags == ["web", "api", "async"]


def test_skill_graph_filtering_by_category_and_language() -> None:
    graph = SkillGraph()
    graph.add_node(
        SkillNode(
            skill_id="node_py",
            name="Python",
            category="programming_language",
            language="Python",
            difficulty="beginner",
        )
    )
    graph.add_node(
        SkillNode(
            skill_id="node_rust",
            name="Rust",
            category="programming_language",
            language="Rust",
            difficulty="advanced",
        )
    )
    graph.add_node(
        SkillNode(
            skill_id="node_react",
            name="React",
            category="frontend_framework",
            language="JavaScript",
            difficulty="intermediate",
        )
    )

    prog_langs = graph.filter_by_category("programming_language")
    assert "Python" in prog_langs
    assert "Rust" in prog_langs
    assert "React" not in prog_langs

    py_skills = graph.filter_by_language("Python")
    assert py_skills == ["Python"]

    js_skills = graph.filter_by_language("javascript")
    assert js_skills == ["React"]


def test_skill_graph_career_roles_catalog() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    roles = graph.get_roles()

    assert "Machine Learning Engineer" in roles
    assert "Backend Developer" in roles
    assert "Frontend Developer" in roles
    assert "Full Stack Developer" in roles
    assert "Mobile Developer" in roles

    ml_skills = graph.get_role_skills("Machine Learning Engineer")
    assert "Python" in ml_skills
    assert "NumPy" in ml_skills
    assert "Machine Learning" in ml_skills

    backend_skills = graph.get_role_skills("Backend Developer")
    assert "Python" in backend_skills
    assert "FastAPI" in backend_skills
    assert "REST APIs" in backend_skills

    assert graph.get_role_skills("Nonexistent Role") == []


def test_skill_graph_cycle_prevention() -> None:
    graph = SkillGraph()
    graph.add_skill("A")
    graph.add_skill("B")
    graph.add_skill("C")

    graph.add_relationship("A", "B", RelationshipType.PREREQUISITE)
    graph.add_relationship("B", "C", RelationshipType.PREREQUISITE)

    with pytest.raises(
        ValueError, match="Circular prerequisite detected|Cycle detected"
    ):
        graph.add_relationship("C", "A", RelationshipType.PREREQUISITE)


def test_skill_graph_export_snapshot() -> None:
    graph = SkillGraphBuilder.build_default_graph()
    data = graph.export_graph()

    assert len(data.skills) > 0
    assert len(data.nodes) > 0
    assert len(data.relationships) > 0

    node_names = {n.name for n in data.nodes}
    assert "Python" in node_names
    assert "FastAPI" in node_names
