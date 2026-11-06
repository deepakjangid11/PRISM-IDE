import uuid

import pytest
from fastapi.testclient import TestClient

from prism.api.dependencies import skill_graph
from prism.api.main import app
from prism.intelligence.models.skill_models import (
    ProficiencyLevel,
    RelationshipType,
    SkillNode,
)


@pytest.fixture(autouse=True)
def setup_api_test_state() -> None:
    # Ensure default graph skills and nodes are present
    if not skill_graph.get_node("python"):
        skill_graph.add_node(
            SkillNode(
                skill_id="node_py",
                name="Python",
                category="programming_language",
                language="Python",
                difficulty="beginner",
            )
        )
    if not skill_graph.get_node("fastapi"):
        skill_graph.add_node(
            SkillNode(
                skill_id="node_fastapi",
                name="FastAPI",
                category="framework",
                language="Python",
                difficulty="intermediate",
            )
        )
        skill_graph.add_relationship("Python", "FastAPI", RelationshipType.PREREQUISITE)


def test_api_record_and_get_evidence() -> None:
    client = TestClient(app)
    dev_id = f"dev_api_test_{uuid.uuid4().hex[:6]}"

    # POST /skills/evidence
    payload = {
        "developer_id": dev_id,
        "skill_name": "FastAPI",
        "description": "Implemented JWT authentication dependency",
        "programming_language": "Python",
        "framework": "FastAPI",
        "evidence_type": "implementation",
        "evidence_strength": 1.2,
        "confidence_score": 0.95,
        "complexity_score": 0.8,
    }
    response = client.post("/skills/evidence", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["developer_id"] == dev_id
    assert data["skill_name"] == "FastAPI"
    assert data["evidence_count"] >= 1

    # GET /skills/evidence/{developer_id}
    res_ev = client.get(f"/skills/evidence/{dev_id}")
    assert res_ev.status_code == 200
    ev_list = res_ev.json()
    assert len(ev_list) >= 1
    assert ev_list[0]["skill_name"] == "FastAPI"

    # GET /skills/profile/{developer_id}
    res_prof = client.get(f"/skills/profile/{dev_id}")
    assert res_prof.status_code == 200
    prof_data = res_prof.json()
    assert prof_data["developer_id"] == dev_id
    assert "fastapi" in prof_data["skills"]


def test_api_skill_proficiency() -> None:
    client = TestClient(app)
    dev_id = f"dev_api_prof_{uuid.uuid4().hex[:6]}"

    # Record 3 pieces of evidence for Python to hit Beginner
    for i in range(1, 4):
        client.post(
            "/skills/evidence",
            json={
                "developer_id": dev_id,
                "skill_name": "Python",
                "description": f"Function {i}",
                "evidence_type": "implementation",
            },
        )

    # GET /skills/proficiency/{developer_id}
    res_all = client.get(f"/skills/proficiency/{dev_id}")
    assert res_all.status_code == 200
    all_skills = res_all.json()
    assert "python" in all_skills
    assert all_skills["python"]["proficiency_level"] == ProficiencyLevel.BEGINNER.value

    # GET /skills/proficiency/{developer_id}/{skill_id}
    res_one = client.get(f"/skills/proficiency/{dev_id}/python")
    assert res_one.status_code == 200
    one_skill = res_one.json()
    assert one_skill["skill_name"] == "Python"
    assert one_skill["proficiency_level"] == ProficiencyLevel.BEGINNER.value


def test_api_skill_graph_endpoints() -> None:
    client = TestClient(app)

    # GET /skills/graph
    res_graph = client.get("/skills/graph")
    assert res_graph.status_code == 200
    graph_data = res_graph.json()
    assert "skills" in graph_data
    assert "nodes" in graph_data
    assert "relationships" in graph_data

    # GET /skills/graph/{skill_id}
    res_node = client.get("/skills/graph/python")
    assert res_node.status_code == 200
    node = res_node.json()
    assert node["name"] == "Python"

    # GET /skills/graph/nonexistent (404)
    res_404 = client.get("/skills/graph/unknown_skill_xyz")
    assert res_404.status_code == 404

    # GET /skills/prerequisites/{skill_id}
    res_prereqs = client.get("/skills/prerequisites/fastapi")
    assert res_prereqs.status_code == 200
    prereqs = res_prereqs.json()
    assert "Python" in prereqs

    # GET /skills/related/{skill_id}
    res_related = client.get("/skills/related/fastapi")
    assert res_related.status_code == 200
    assert isinstance(res_related.json(), list)


def test_api_gap_analysis_and_recommendations() -> None:
    client = TestClient(app)
    dev_id = f"dev_api_gap_{uuid.uuid4().hex[:6]}"

    # Record 3 Python items
    for i in range(1, 4):
        client.post(
            "/skills/evidence",
            json={
                "developer_id": dev_id,
                "skill_name": "Python",
                "description": f"Script {i}",
            },
        )

    # POST /skills/gap-analysis for Machine Learning Engineer
    res_gaps = client.post(
        "/skills/gap-analysis",
        json={"developer_id": dev_id, "target_role": "Machine Learning Engineer"},
    )
    assert res_gaps.status_code == 200
    gaps = res_gaps.json()
    assert len(gaps) > 0
    gap_skills = {g["missing_skill"] for g in gaps}
    assert "Machine Learning" in gap_skills

    # GET /skills/gaps/{developer_id}
    res_get_gaps = client.get(
        f"/skills/gaps/{dev_id}?target_role=Machine%20Learning%20Engineer"
    )
    assert res_get_gaps.status_code == 200
    assert len(res_get_gaps.json()) > 0

    # GET /skills/recommendations/{developer_id}
    res_recs = client.get(
        f"/skills/recommendations/{dev_id}?target_role=Machine%20Learning%20Engineer"
    )
    assert res_recs.status_code == 200
    recs = res_recs.json()
    assert len(recs) > 0
    assert "priority_level" in recs[0]
    assert "estimated_effort_hours" in recs[0]


def test_api_learning_path_endpoints() -> None:
    client = TestClient(app)
    dev_id = f"dev_api_path_{uuid.uuid4().hex[:6]}"

    # POST /skills/learning-path
    res_post_path = client.post(
        "/skills/learning-path",
        json={"developer_id": dev_id, "target_role": "Backend Developer"},
    )
    assert res_post_path.status_code == 200
    path_data = res_post_path.json()
    assert path_data["developer_id"] == dev_id
    assert path_data["target_role"] == "Backend Developer"
    assert len(path_data["steps"]) > 0

    # GET /skills/learning-path/{developer_id}
    res_get_path = client.get(
        f"/skills/learning-path/{dev_id}?target_role=Backend%20Developer"
    )
    assert res_get_path.status_code == 200
    assert res_get_path.json()["target_role"] == "Backend Developer"


def test_api_skill_graph_filters_and_queries() -> None:
    client = TestClient(app)

    # Filter by category
    res_cat = client.get("/skills/graph?category=framework")
    assert res_cat.status_code == 200
    assert len(res_cat.json()["nodes"]) >= 1

    # Filter by language
    res_lang = client.get("/skills/graph?language=Python")
    assert res_lang.status_code == 200
    assert len(res_lang.json()["nodes"]) >= 1

    # 404 on unknown skill prerequisites
    res_bad_prereq = client.get("/skills/prerequisites/unknown_skill_xyz")
    assert res_bad_prereq.status_code == 404

    # 404 on unknown skill related
    res_bad_related = client.get("/skills/related/unknown_skill_xyz")
    assert res_bad_related.status_code == 404


def test_api_gap_and_recommendation_target_goal_and_defaults() -> None:
    client = TestClient(app)
    dev_id = f"dev_api_def_{uuid.uuid4().hex[:6]}"

    # Record 3 Python items
    for i in range(1, 4):
        client.post(
            "/skills/evidence",
            json={
                "developer_id": dev_id,
                "skill_name": "Python",
                "description": f"Script {i}",
            },
        )

    # POST /skills/gap-analysis with target_goal
    res_goal = client.post(
        "/skills/gap-analysis",
        json={"developer_id": dev_id, "target_goal": "FastAPI"},
    )
    assert res_goal.status_code == 200

    # GET /skills/gaps with target_goal
    res_get_goal = client.get(f"/skills/gaps/{dev_id}?target_goal=FastAPI")
    assert res_get_goal.status_code == 200

    # GET /skills/gaps without parameters (default over registered skills)
    res_get_def = client.get(f"/skills/gaps/{dev_id}")
    assert res_get_def.status_code == 200

    # GET /skills/recommendations with target_goal
    res_rec_goal = client.get(f"/skills/recommendations/{dev_id}?target_goal=FastAPI")
    assert res_rec_goal.status_code == 200

    # GET /skills/recommendations default
    res_rec_def = client.get(f"/skills/recommendations/{dev_id}")
    assert res_rec_def.status_code == 200

    # POST /skills/learning-path with target_goal
    res_path_goal = client.post(
        "/skills/learning-path",
        json={"developer_id": dev_id, "target_goal": "FastAPI"},
    )
    assert res_path_goal.status_code == 200

    # GET /skills/learning-path with target_goal
    res_get_path_goal = client.get(
        f"/skills/learning-path/{dev_id}?target_goal=FastAPI"
    )
    assert res_get_path_goal.status_code == 200


def test_api_validation_errors() -> None:
    client = TestClient(app)

    # Empty developer_id in profile
    res_empty_dev = client.get("/skills/profile/%20")
    assert res_empty_dev.status_code == 400

    # Missing targets in gap analysis
    res_missing_gap = client.post("/skills/gap-analysis", json={"developer_id": "dev1"})
    assert res_missing_gap.status_code == 400

    # Missing targets in learning path
    res_missing_path = client.post(
        "/skills/learning-path", json={"developer_id": "dev1"}
    )
    assert res_missing_path.status_code == 400


def test_api_skills_error_and_edge_branches() -> None:
    from unittest.mock import patch

    from prism.api.dependencies import (
        gap_analyzer,
        path_generator,
        rec_engine,
        skill_repo,
        skill_tracker,
    )

    client = TestClient(app)

    # 1. Empty developer_id validation across endpoints
    assert client.get("/skills/evidence/%20").status_code == 400
    assert client.get("/skills/proficiency/%20").status_code == 400
    assert client.get("/skills/proficiency/dev_test/%20").status_code == 400
    assert client.get("/skills/gaps/%20").status_code == 400
    assert client.get("/skills/recommendations/%20").status_code == 400
    assert (
        client.get("/skills/learning-path/%20?target_goal=FastAPI").status_code == 400
    )
    assert client.get("/skills/learning-path/dev_test").status_code == 400

    # 2. POST /skills/evidence error branches
    valid_payload = {
        "developer_id": "dev_test",
        "skill_name": "Python",
        "description": "Code contribution",
        "evidence_type": "implementation",
    }
    with patch.object(
        skill_tracker, "record_evidence", side_effect=ValueError("Invalid skill name")
    ):
        assert client.post("/skills/evidence", json=valid_payload).status_code == 400

    with patch.object(
        skill_tracker, "record_evidence", side_effect=RuntimeError("Storage crash")
    ):
        assert client.post("/skills/evidence", json=valid_payload).status_code == 500

    # 3. GET /skills/profile/{dev} error branches
    with patch.object(
        skill_tracker, "get_profile", side_effect=ValueError("Bad dev id")
    ):
        assert client.get("/skills/profile/dev_test").status_code == 400

    with patch.object(
        skill_tracker, "get_profile", side_effect=RuntimeError("Database failure")
    ):
        assert client.get("/skills/profile/dev_test").status_code == 500

    # 4. Error branches across skills GET routes
    with patch.object(
        skill_repo, "get_evidence", side_effect=RuntimeError("Repo failure")
    ):
        assert client.get("/skills/evidence/dev_test").status_code == 500

    with patch.object(
        gap_analyzer, "identify_gaps", side_effect=ValueError("Invalid gap query")
    ):
        assert (
            client.get("/skills/gaps/dev_test?target_goal=FastAPI").status_code == 400
        )
        assert (
            client.post(
                "/skills/gap-analysis",
                json={"developer_id": "dev_test", "target_goal": "FastAPI"},
            ).status_code
            == 400
        )

    with patch.object(
        rec_engine, "generate_recommendations", side_effect=ValueError("Rec error")
    ):
        assert (
            client.get(
                "/skills/recommendations/dev_test?target_goal=FastAPI"
            ).status_code
            == 400
        )

    with patch.object(
        path_generator, "generate_path", side_effect=ValueError("Path error")
    ):
        assert (
            client.get("/skills/learning-path/dev_test?target_goal=FastAPI").status_code
            == 400
        )
        assert (
            client.post(
                "/skills/learning-path",
                json={"developer_id": "dev_test", "target_goal": "FastAPI"},
            ).status_code
            == 400
        )

    # 5. Fallback in GET /skills/evidence/{dev_id} when skill_repo returns empty
    with patch.object(skill_repo, "get_evidence", return_value=[]):
        assert client.get("/skills/evidence/dev_test").status_code == 200
        assert (
            client.get("/skills/evidence/dev_test?skill_name=python").status_code == 200
        )

    # 6. /skills/graph/{skill_id} 404 on missing
    assert client.get("/skills/graph/non_existent_skill_xyz").status_code == 404
