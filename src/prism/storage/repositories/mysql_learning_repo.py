from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from prism.learning.models import LearningProgress
from prism.storage.database import session_scope
from prism.storage.models.learning_records import (
    LearningProgressHistoryRecord,
    LearningProgressItemRecord,
    LearningProgressRecord,
)
from prism.storage.repositories.mysql_developer_repo import (
    MySQLDeveloperRepository,
)
from prism.storage.repositories.mysql_graph_repo import (
    MySQLSkillGraphRepository,
)


class MySQLLearningRepository:
    """MySQL-backed repository for learning roadmaps, normalized items, and audit history."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        developer_repo: MySQLDeveloperRepository | None = None,
        graph_repo: MySQLSkillGraphRepository | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.developer_repo = developer_repo or MySQLDeveloperRepository(
            session_factory
        )
        self.graph_repo = graph_repo or MySQLSkillGraphRepository(session_factory)

    def save_progress(
        self,
        progress: LearningProgress,
        path_steps: list[str] | None = None,
        change_summary: str | None = None,
    ) -> None:
        """Persist active progress, normalized item records, and log an audit history snapshot."""
        dev_id = progress.developer_id.strip()
        self.developer_repo.ensure_developer(dev_id)

        target_name = progress.target_goal.strip()
        target_skill_id = self.graph_repo.get_skill_id_by_name(target_name)
        if not target_skill_id:
            slug = target_name.lower().replace(" ", "_").replace("/", "_")
            target_skill_id = f"skill_{slug}"
            self.graph_repo.register_skill(target_skill_id, target_name)

        now = datetime.now(UTC)
        steps = (
            path_steps
            or progress.completed_skills
            + progress.in_progress_skills
            + progress.remaining_skills
        )

        with session_scope(self.session_factory) as session:
            # 1. Upsert learning_progress record
            stmt = select(LearningProgressRecord).where(
                LearningProgressRecord.developer_id == dev_id,
                LearningProgressRecord.target_goal_skill_id == target_skill_id,
            )
            prog_record = session.scalar(stmt)
            if prog_record is None:
                prog_record = LearningProgressRecord(
                    developer_id=dev_id,
                    target_goal_skill_id=target_skill_id,
                    completion_percentage=progress.completion_percentage,
                    created_at=now,
                    updated_at=now,
                )
                session.add(prog_record)
                session.flush()  # populate prog_record.progress_id
            else:
                prog_record.completion_percentage = progress.completion_percentage
                prog_record.updated_at = now
                session.flush()

            progress_id = prog_record.progress_id

            # 2. Sync normalized learning_progress_items
            # Clear old items for this progress and re-insert normalized steps
            del_stmt = delete(LearningProgressItemRecord).where(
                LearningProgressItemRecord.progress_id == progress_id
            )
            session.execute(del_stmt)

            for order, step_name in enumerate(steps, 1):
                s_id = self.graph_repo.get_skill_id_by_name(step_name)
                if not s_id:
                    s_slug = step_name.lower().replace(" ", "_").replace("/", "_")
                    s_id = f"skill_{s_slug}"
                    self.graph_repo.register_skill(s_id, step_name)

                status = (
                    "completed"
                    if step_name in progress.completed_skills
                    else (
                        "in_progress"
                        if step_name in progress.in_progress_skills
                        else "remaining"
                    )
                )

                item_record = LearningProgressItemRecord(
                    progress_id=progress_id,
                    skill_id=s_id,
                    status=status,
                    step_order=order,
                    completed_at=now if status == "completed" else None,
                )
                session.add(item_record)

            # 3. Log historical checkpoint snapshot
            history_record = LearningProgressHistoryRecord(
                progress_id=progress_id,
                developer_id=dev_id,
                target_goal_skill_id=target_skill_id,
                completed_count=len(progress.completed_skills),
                total_steps=len(steps),
                completion_percentage=progress.completion_percentage,
                change_summary=(
                    change_summary
                    or f"Progress update: {progress.completion_percentage:.1f}%"
                ),
                recorded_at=now,
            )
            session.add(history_record)

    def get_progress(
        self, developer_id: str, target_goal: str
    ) -> LearningProgress | None:
        """Fetch active learning progress by reconstructing normalized items."""
        dev_id = developer_id.strip()
        target_skill_id = self.graph_repo.get_skill_id_by_name(target_goal)
        if not target_skill_id:
            return None

        with session_scope(self.session_factory) as session:
            stmt = select(LearningProgressRecord).where(
                LearningProgressRecord.developer_id == dev_id,
                LearningProgressRecord.target_goal_skill_id == target_skill_id,
            )
            prog_record = session.scalar(stmt)
            if prog_record is None:
                return None

            # Fetch normalized items
            items_stmt = (
                select(LearningProgressItemRecord)
                .where(
                    LearningProgressItemRecord.progress_id == prog_record.progress_id
                )
                .order_by(LearningProgressItemRecord.step_order.asc())
            )
            items = session.scalars(items_stmt).all()

            completed_skills: list[str] = []
            in_progress_skills: list[str] = []
            remaining_skills: list[str] = []

            for item in items:
                skill_name = (
                    self.graph_repo.get_skill_name_by_id(item.skill_id) or item.skill_id
                )
                if item.status == "completed":
                    completed_skills.append(skill_name)
                elif item.status == "in_progress":
                    in_progress_skills.append(skill_name)
                else:
                    remaining_skills.append(skill_name)

            return LearningProgress(
                developer_id=dev_id,
                target_goal=target_goal.strip(),
                completed_skills=completed_skills,
                in_progress_skills=in_progress_skills,
                remaining_skills=remaining_skills,
                completion_percentage=prog_record.completion_percentage,
            )

    def get_progress_history(
        self, developer_id: str, target_goal: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve temporal progression audit history."""
        dev_id = developer_id.strip()
        target_skill_id = (
            self.graph_repo.get_skill_id_by_name(target_goal) if target_goal else None
        )

        with session_scope(self.session_factory) as session:
            stmt = select(LearningProgressHistoryRecord).where(
                LearningProgressHistoryRecord.developer_id == dev_id
            )
            if target_skill_id:
                stmt = stmt.where(
                    LearningProgressHistoryRecord.target_goal_skill_id
                    == target_skill_id
                )
            stmt = stmt.order_by(LearningProgressHistoryRecord.recorded_at.desc())

            records = session.scalars(stmt).all()
            return [
                {
                    "history_id": r.history_id,
                    "progress_id": r.progress_id,
                    "developer_id": r.developer_id,
                    "target_goal_skill_id": r.target_goal_skill_id,
                    "target_goal": (
                        self.graph_repo.get_skill_name_by_id(r.target_goal_skill_id)
                        or r.target_goal_skill_id
                    ),
                    "completed_count": r.completed_count,
                    "total_steps": r.total_steps,
                    "completion_percentage": r.completion_percentage,
                    "change_summary": r.change_summary,
                    "recorded_at": r.recorded_at,
                }
                for r in records
            ]
