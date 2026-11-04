from datetime import UTC, datetime

from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    ProficiencyLevel,
    RelationshipType,
    SkillEvidence,
    SkillRelationship,
)
from prism.learning.models import LearningProgress
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryLearningRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
)


def test_in_memory_developer_repo() -> None:
    repo = InMemoryDeveloperRepository()
    assert repo.list_developers() == []

    repo.ensure_developer("dev_1", name="Alice", email="alice@example.com")
    assert repo.list_developers() == ["dev_1"]

    dev_data = repo.get_developer("dev_1")
    assert dev_data is not None
    assert dev_data["name"] == "Alice"
    assert dev_data["email"] == "alice@example.com"

    # Ensure idempotency / update
    repo.ensure_developer("dev_1", name="Alice J.")
    updated = repo.get_developer("dev_1")
    assert updated is not None
    assert updated["name"] == "Alice J."


def test_in_memory_activity_repo() -> None:
    dev_repo = InMemoryDeveloperRepository()
    act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    now = datetime.now(UTC)

    act1 = DeveloperActivity(
        event_id="evt_1",
        developer_id="dev_2",
        event_type="git_commit",
        timestamp=now,
        project_path="/projects/prism",
        file_path="src/main.py",
        metadata={"commit_hash": "abc1234"},
    )
    act2 = DeveloperActivity(
        event_id="evt_2",
        developer_id="dev_2",
        event_type="test_run",
        timestamp=now,
        project_path="/projects/other",
        file_path="tests/test_main.py",
    )
    act_repo.save_many([act1, act2])

    assert "dev_2" in dev_repo.list_developers()
    all_acts = act_repo.get_by_developer("dev_2")
    assert len(all_acts) == 2

    prism_acts = act_repo.get_by_developer("dev_2", project_path="/projects/prism")
    assert len(prism_acts) == 1
    assert prism_acts[0].event_id == "evt_1"

    act_repo.clear("dev_2")
    assert act_repo.get_by_developer("dev_2") == []


def test_in_memory_skill_graph_repo() -> None:
    repo = InMemorySkillGraphRepository()
    skill_id = repo.register_skill("sk_fastapi", "FastAPI", category="Framework")
    assert skill_id == "sk_fastapi"
    assert repo.get_skill_id_by_name("FastAPI") == "sk_fastapi"
    assert repo.get_skill_id_by_name("fastapi") == "sk_fastapi"
    assert repo.get_skill_name_by_id("sk_fastapi") == "FastAPI"

    repo.register_skill("sk_python", "Python", category="Language")
    rel = SkillRelationship(
        from_skill="Python",
        to_skill="FastAPI",
        relationship_type=RelationshipType.PREREQUISITE,
    )
    repo.add_relationship(rel)

    assert set(repo.get_skills()) == {"FastAPI", "Python"}
    rels = repo.get_relationships()
    assert len(rels) == 1
    assert rels[0].from_skill == "Python"
    assert rels[0].to_skill == "FastAPI"


def test_in_memory_skill_repo() -> None:
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    skill_repo = InMemorySkillRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    now = datetime.now(UTC)

    ev = SkillEvidence(
        evidence_id="ev_101",
        developer_id="dev_3",
        skill_name="Python",
        evidence_type="code_artifact",
        description="Implemented AST visitor",
        timestamp=now,
    )
    skill_repo.record_evidence(ev)

    dev_evidence = skill_repo.get_evidence("dev_3", "Python")
    assert len(dev_evidence) == 1
    assert dev_evidence[0].evidence_id == "ev_101"

    assessment = DeveloperSkill(
        developer_id="dev_3",
        skill_name="Python",
        proficiency_level=ProficiencyLevel.INTERMEDIATE,
        evidence_count=6,
        evidence_list=[ev],
        has_sufficient_evidence=True,
        last_assessed=now,
    )
    skill_repo.save_skill_assessment(assessment)

    profile = skill_repo.get_profile("dev_3")
    assert "python" in profile.skills
    assert profile.skills["python"].proficiency_level == ProficiencyLevel.INTERMEDIATE
    assert "dev_3" in skill_repo.list_developers()


def test_in_memory_learning_repo() -> None:
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    learning_repo = InMemoryLearningRepository(dev_repo=dev_repo, graph_repo=graph_repo)

    progress = LearningProgress(
        developer_id="dev_4",
        target_goal="Machine Learning",
        completed_skills=["Python", "NumPy"],
        in_progress_skills=["Pandas"],
        remaining_skills=["Statistics", "Machine Learning"],
        completion_percentage=40.0,
    )
    learning_repo.save_progress(
        progress,
        path_steps=[
            "Python",
            "NumPy",
            "Pandas",
            "Statistics",
            "Machine Learning",
        ],
        change_summary="Completed NumPy module",
    )

    retrieved = learning_repo.get_progress("dev_4", "Machine Learning")
    assert retrieved is not None
    assert retrieved.completed_skills == ["Python", "NumPy"]
    assert retrieved.completion_percentage == 40.0

    history = learning_repo.get_progress_history("dev_4", "Machine Learning")
    assert len(history) == 1
    assert history[0]["completed_count"] == 2
    assert history[0]["total_steps"] == 5
    assert history[0]["completion_percentage"] == 40.0
    assert history[0]["change_summary"] == "Completed NumPy module"
