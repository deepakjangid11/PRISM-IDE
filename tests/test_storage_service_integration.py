from datetime import UTC, datetime

from prism.intelligence.developer_activity import ActivityRecorder
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.skill_models import (
    ProficiencyLevel,
    RelationshipType,
    SkillEvidence,
)
from prism.intelligence.skill_graph import SkillGraph
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.models import LearningPath
from prism.learning.progress_tracker import LearningProgressTracker
from prism.storage.repositories.memory_repo import (
    InMemoryActivityRepository,
    InMemoryDeveloperRepository,
    InMemoryLearningRepository,
    InMemorySkillGraphRepository,
    InMemorySkillRepository,
)


def test_activity_recorder_with_repository() -> None:
    dev_repo = InMemoryDeveloperRepository()
    act_repo = InMemoryActivityRepository(dev_repo=dev_repo)
    recorder = ActivityRecorder(repository=act_repo)

    now = datetime.now(UTC)
    act = DeveloperActivity(
        event_id="evt_rec_1",
        developer_id="dev_rec",
        event_type="git_push",
        timestamp=now,
        project_path="/repo/prism",
        file_path="src/app.py",
    )
    recorder.record(act)

    # In-memory list
    assert len(recorder.get_activities()) == 1
    # Filtered by developer
    dev_acts = recorder.get_activities_for_developer("dev_rec")
    assert len(dev_acts) == 1
    assert dev_acts[0].event_id == "evt_rec_1"
    # Persisted in repo
    assert len(act_repo.get_by_developer("dev_rec")) == 1

    # Clear
    recorder.clear()
    assert recorder.get_activities() == []
    assert act_repo.get_by_developer("dev_rec") == []


def test_skill_tracker_with_repository() -> None:
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    skill_repo = InMemorySkillRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    tracker = SkillTracker(repository=skill_repo, developer_repo=dev_repo)

    now = datetime.now(UTC)
    ev = SkillEvidence(
        evidence_id="ev_track_1",
        developer_id="dev_alpha",
        skill_name="Python",
        evidence_type="commit",
        description="Refactored storage",
        timestamp=now,
    )
    dev_skill = tracker.record_evidence(ev)
    assert dev_skill.evidence_count == 1
    assert dev_skill.proficiency_level == ProficiencyLevel.INSUFFICIENT_DATA

    # Check persistence in repository
    repo_profile = skill_repo.get_profile("dev_alpha")
    assert "python" in repo_profile.skills
    assert repo_profile.skills["python"].evidence_count == 1

    # New tracker reading from same repository
    tracker2 = SkillTracker(repository=skill_repo, developer_repo=dev_repo)
    reloaded_profile = tracker2.get_profile("dev_alpha")
    assert "python" in reloaded_profile.skills
    assert "dev_alpha" in tracker2.list_developers()


def test_skill_graph_with_repository() -> None:
    graph_repo = InMemorySkillGraphRepository()
    graph = SkillGraph(repository=graph_repo)

    graph.add_skill("Python")
    graph.add_skill("FastAPI")
    graph.add_relationship("Python", "FastAPI", RelationshipType.PREREQUISITE)

    # Repository should contain the data
    assert "Python" in graph_repo.get_skills()
    assert "FastAPI" in graph_repo.get_skills()
    assert len(graph_repo.get_relationships()) == 1

    # New graph loading from repository should immediately restore topology
    restored_graph = SkillGraph(repository=graph_repo)
    assert restored_graph.has_skill("Python")
    assert restored_graph.has_skill("FastAPI")
    assert restored_graph.get_prerequisites("FastAPI") == ["Python"]


def test_learning_progress_tracker_with_repository() -> None:
    dev_repo = InMemoryDeveloperRepository()
    graph_repo = InMemorySkillGraphRepository()
    learning_repo = InMemoryLearningRepository(dev_repo=dev_repo, graph_repo=graph_repo)
    tracker = LearningProgressTracker(repository=learning_repo)

    dev_tracker = SkillTracker()
    now = datetime.now(UTC)
    # Add 3 evidences to satisfy threshold
    for i in range(3):
        dev_tracker.record_evidence(
            SkillEvidence(
                evidence_id=f"ev_p_{i}",
                developer_id="dev_beta",
                skill_name="Python",
                evidence_type="code_artifact",
                description=f"Task {i}",
                timestamp=now,
            )
        )
    profile = dev_tracker.get_profile("dev_beta")

    learning_path = LearningPath(
        path_id="path_beta_1",
        developer_id="dev_beta",
        target_goal="FastAPI Services",
        steps=["Python", "FastAPI"],
        estimated_steps=2,
    )

    progress = tracker.track_progress(profile, learning_path)
    assert progress.completed_skills == ["Python"]
    assert progress.remaining_skills == ["FastAPI"]
    assert progress.completion_percentage == 50.0

    # Retrieve from repository through tracker
    persisted = tracker.get_progress("dev_beta", "FastAPI Services")
    assert persisted is not None
    assert persisted.completed_skills == ["Python"]

    history = tracker.get_progress_history("dev_beta", "FastAPI Services")
    assert len(history) == 1
    assert history[0]["completion_percentage"] == 50.0
