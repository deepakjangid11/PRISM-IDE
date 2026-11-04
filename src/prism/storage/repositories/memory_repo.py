from datetime import UTC, datetime
from typing import Any

from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    DeveloperSkillProfile,
    SkillEvidence,
    SkillRelationship,
)
from prism.learning.models import LearningProgress


class InMemoryDeveloperRepository:
    """In-memory implementation of DeveloperRepository for testing and offline execution."""

    def __init__(self) -> None:
        self._developers: dict[str, dict[str, Any]] = {}

    def ensure_developer(
        self,
        developer_id: str,
        name: str | None = None,
        email: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        if developer_id not in self._developers:
            self._developers[developer_id] = {
                "developer_id": developer_id,
                "name": name,
                "email": email,
                "created_at": now,
                "updated_at": now,
            }
        else:
            self._developers[developer_id]["updated_at"] = now
            if name:
                self._developers[developer_id]["name"] = name
            if email:
                self._developers[developer_id]["email"] = email

    def get_developer(self, developer_id: str) -> dict[str, Any] | None:
        return self._developers.get(developer_id)

    def list_developers(self) -> list[str]:
        return sorted(self._developers.keys())


class InMemoryActivityRepository:
    """In-memory implementation of ActivityRepository."""

    def __init__(self, dev_repo: InMemoryDeveloperRepository | None = None) -> None:
        self._activities: list[DeveloperActivity] = []
        self._dev_repo = dev_repo or InMemoryDeveloperRepository()

    def save(self, activity: DeveloperActivity) -> None:
        self._dev_repo.ensure_developer(activity.developer_id)
        self._activities.append(activity)

    def save_many(self, activities: list[DeveloperActivity]) -> None:
        for act in activities:
            self.save(act)

    def get_by_developer(
        self, developer_id: str, project_path: str | None = None
    ) -> list[DeveloperActivity]:
        return [
            a
            for a in self._activities
            if a.developer_id == developer_id
            and (project_path is None or a.project_path == project_path)
        ]

    def clear(self, developer_id: str | None = None) -> None:
        if developer_id is None:
            self._activities.clear()
        else:
            self._activities = [
                a for a in self._activities if a.developer_id != developer_id
            ]


class InMemorySkillGraphRepository:
    """In-memory implementation of SkillGraphRepository."""

    def __init__(self) -> None:
        # skill_id -> skill_name
        self._id_to_name: dict[str, str] = {}
        # skill_name (case-insensitive) -> skill_id
        self._name_to_id: dict[str, str] = {}
        self._canonical_names: dict[str, str] = {}
        self._relationships: list[SkillRelationship] = []

    def register_skill(
        self, skill_id: str, skill_name: str, category: str | None = None
    ) -> str:
        canonical = skill_name.strip()
        lower = canonical.lower()
        if lower in self._name_to_id:
            return self._name_to_id[lower]
        self._id_to_name[skill_id] = canonical
        self._name_to_id[lower] = skill_id
        self._canonical_names[skill_id] = canonical
        return skill_id

    def get_skill_id_by_name(self, skill_name: str) -> str | None:
        return self._name_to_id.get(skill_name.strip().lower())

    def get_skill_name_by_id(self, skill_id: str) -> str | None:
        return self._id_to_name.get(skill_id)

    def add_relationship(self, relationship: SkillRelationship) -> None:
        if self.get_skill_id_by_name(relationship.from_skill) is None:
            self.register_skill(
                relationship.from_skill.lower().replace(" ", "_"),
                relationship.from_skill,
            )
        if self.get_skill_id_by_name(relationship.to_skill) is None:
            self.register_skill(
                relationship.to_skill.lower().replace(" ", "_"),
                relationship.to_skill,
            )
        # Check duplicate
        for r in self._relationships:
            if (
                r.from_skill.lower() == relationship.from_skill.lower()
                and r.to_skill.lower() == relationship.to_skill.lower()
                and r.relationship_type == relationship.relationship_type
            ):
                return
        self._relationships.append(relationship)

    def get_skills(self) -> list[str]:
        return sorted(self._id_to_name.values())

    def get_relationships(self) -> list[SkillRelationship]:
        return list(self._relationships)


class InMemorySkillRepository:
    """In-memory implementation of SkillRepository."""

    def __init__(
        self,
        dev_repo: InMemoryDeveloperRepository | None = None,
        graph_repo: InMemorySkillGraphRepository | None = None,
    ) -> None:
        self._dev_repo = dev_repo or InMemoryDeveloperRepository()
        self._graph_repo = graph_repo or InMemorySkillGraphRepository()
        self._evidence: dict[str, list[SkillEvidence]] = {}
        self._profiles: dict[str, DeveloperSkillProfile] = {}

    def record_evidence(self, evidence: SkillEvidence) -> None:
        dev_id = evidence.developer_id
        self._dev_repo.ensure_developer(dev_id)
        if dev_id not in self._evidence:
            self._evidence[dev_id] = []
        self._evidence[dev_id].append(evidence)

    def get_evidence(
        self, developer_id: str, skill_name: str | None = None
    ) -> list[SkillEvidence]:
        all_ev = self._evidence.get(developer_id, [])
        if skill_name is None:
            return list(all_ev)
        target = skill_name.strip().lower()
        return [e for e in all_ev if e.skill_name.strip().lower() == target]

    def save_skill_assessment(self, skill: DeveloperSkill) -> None:
        dev_id = skill.developer_id
        self._dev_repo.ensure_developer(dev_id)
        if dev_id not in self._profiles:
            self._profiles[dev_id] = DeveloperSkillProfile(
                developer_id=dev_id,
                skills={},
                last_updated=datetime.now(UTC),
            )
        profile = self._profiles[dev_id]
        profile.skills[skill.skill_name.strip().lower()] = skill
        profile.last_updated = datetime.now(UTC)

    def get_profile(self, developer_id: str) -> DeveloperSkillProfile:
        self._dev_repo.ensure_developer(developer_id)
        if developer_id not in self._profiles:
            self._profiles[developer_id] = DeveloperSkillProfile(
                developer_id=developer_id,
                skills={},
                last_updated=datetime.now(UTC),
            )
        return self._profiles[developer_id]

    def list_developers(self) -> list[str]:
        return sorted(self._dev_repo.list_developers())


class InMemoryLearningRepository:
    """In-memory implementation of LearningRepository with normalized items and audit history."""

    def __init__(
        self,
        dev_repo: InMemoryDeveloperRepository | None = None,
        graph_repo: InMemorySkillGraphRepository | None = None,
    ) -> None:
        self._dev_repo = dev_repo or InMemoryDeveloperRepository()
        self._graph_repo = graph_repo or InMemorySkillGraphRepository()
        # key: (dev_id, target_goal) -> LearningProgress
        self._progress: dict[tuple[str, str], LearningProgress] = {}
        self._items: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._history: list[dict[str, Any]] = []

    def save_progress(
        self,
        progress: LearningProgress,
        path_steps: list[str] | None = None,
        change_summary: str | None = None,
    ) -> None:
        dev_id = progress.developer_id
        goal = progress.target_goal
        self._dev_repo.ensure_developer(dev_id)
        key = (dev_id, goal)
        self._progress[key] = progress

        # Normalize items
        steps = (
            path_steps
            or progress.completed_skills
            + progress.in_progress_skills
            + progress.remaining_skills
        )
        items: list[dict[str, Any]] = []
        for idx, step in enumerate(steps, 1):
            status = (
                "completed"
                if step in progress.completed_skills
                else (
                    "in_progress"
                    if step in progress.in_progress_skills
                    else "remaining"
                )
            )
            items.append(
                {
                    "skill_name": step,
                    "status": status,
                    "step_order": idx,
                    "completed_at": (
                        datetime.now(UTC) if status == "completed" else None
                    ),
                }
            )
        self._items[key] = items

        # Audit history snapshot
        self._history.append(
            {
                "developer_id": dev_id,
                "target_goal": goal,
                "completed_count": len(progress.completed_skills),
                "total_steps": len(steps),
                "completion_percentage": progress.completion_percentage,
                "change_summary": change_summary or f"Updated {goal} progress",
                "recorded_at": datetime.now(UTC),
            }
        )

    def get_progress(
        self, developer_id: str, target_goal: str
    ) -> LearningProgress | None:
        return self._progress.get((developer_id, target_goal))

    def get_progress_history(
        self, developer_id: str, target_goal: str | None = None
    ) -> list[dict[str, Any]]:
        return [
            h
            for h in self._history
            if h["developer_id"] == developer_id
            and (target_goal is None or h["target_goal"] == target_goal)
        ]
