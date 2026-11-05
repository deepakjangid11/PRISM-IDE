from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
)
from prism.storage.database import session_scope
from prism.storage.models.activity_records import DeveloperActivityRecord
from prism.storage.repositories.mysql_developer_repo import (
    MySQLDeveloperRepository,
)


class MySQLActivityRepository:
    """MySQL-backed repository for developer activity streams."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        developer_repo: MySQLDeveloperRepository | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.developer_repo = developer_repo or MySQLDeveloperRepository(
            session_factory
        )

    def save(self, activity: DeveloperActivity) -> None:
        """Persist a single activity event after ensuring developer existence."""
        self.developer_repo.ensure_developer(activity.developer_id)
        with session_scope(self.session_factory) as session:
            record = DeveloperActivityRecord(
                event_id=activity.event_id,
                developer_id=activity.developer_id,
                session_id=activity.session_id,
                project_path=activity.project_path,
                event_type=activity.event_type,
                timestamp=activity.timestamp,
                file_path=activity.file_path,
                metadata_json=dict(activity.metadata),
            )
            session.merge(record)

    def save_many(self, activities: list[DeveloperActivity]) -> None:
        """Persist multiple activity events in an atomic batch."""
        if not activities:
            return

        # Ensure all distinct developers exist
        distinct_devs = {a.developer_id for a in activities}
        for dev_id in distinct_devs:
            self.developer_repo.ensure_developer(dev_id)

        with session_scope(self.session_factory) as session:
            for activity in activities:
                record = DeveloperActivityRecord(
                    event_id=activity.event_id,
                    developer_id=activity.developer_id,
                    session_id=activity.session_id,
                    project_path=activity.project_path,
                    event_type=activity.event_type,
                    timestamp=activity.timestamp,
                    file_path=activity.file_path,
                    metadata_json=dict(activity.metadata),
                )
                session.merge(record)

    def get_by_developer(
        self, developer_id: str, project_path: str | None = None
    ) -> list[DeveloperActivity]:
        """Fetch chronological activities for a developer."""
        with session_scope(self.session_factory) as session:
            stmt = select(DeveloperActivityRecord).where(
                DeveloperActivityRecord.developer_id == developer_id.strip()
            )
            if project_path:
                stmt = stmt.where(
                    DeveloperActivityRecord.project_path == project_path.strip()
                )
            stmt = stmt.order_by(DeveloperActivityRecord.timestamp.asc())

            records = session.scalars(stmt).all()
            return [
                DeveloperActivity(
                    event_id=r.event_id,
                    developer_id=r.developer_id,
                    project_path=r.project_path,
                    event_type=r.event_type,
                    timestamp=r.timestamp,
                    file_path=r.file_path,
                    session_id=r.session_id,
                    metadata=dict(r.metadata_json or {}),
                )
                for r in records
            ]

    def get_history(
        self,
        developer_id: str,
        project_path: str | None = None,
        session_id: str | None = None,
        language: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DeveloperActivity], int]:
        """Fetch filtered and paginated activities with total count."""
        with session_scope(self.session_factory) as session:
            stmt = select(DeveloperActivityRecord).where(
                DeveloperActivityRecord.developer_id == developer_id.strip()
            )
            if project_path:
                stmt = stmt.where(
                    DeveloperActivityRecord.project_path == project_path.strip()
                )
            if session_id:
                stmt = stmt.where(
                    DeveloperActivityRecord.session_id == session_id.strip()
                )

            records = session.scalars(
                stmt.order_by(DeveloperActivityRecord.timestamp.desc())
            ).all()

            activities = [
                DeveloperActivity(
                    event_id=r.event_id,
                    developer_id=r.developer_id,
                    project_path=r.project_path,
                    event_type=r.event_type,
                    timestamp=r.timestamp,
                    file_path=r.file_path,
                    session_id=r.session_id,
                    metadata=dict(r.metadata_json or {}),
                )
                for r in records
            ]

            if language:
                lang_lower = language.lower().strip()
                activities = [
                    a
                    for a in activities
                    if (
                        a.metadata.get("classification", {}).get("language", "").lower()
                        == lang_lower
                        or a.metadata.get("language", "").lower() == lang_lower
                    )
                ]
            if category:
                cat_lower = category.lower().strip()
                activities = [
                    a
                    for a in activities
                    if a.metadata.get("classification", {}).get("category", "").lower()
                    == cat_lower
                ]

            total_count = len(activities)
            paged = activities[offset : offset + limit]
            return paged, total_count

    def get_by_session(self, session_id: str) -> list[DeveloperActivity]:
        """Fetch chronological activities associated with a specific session."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(DeveloperActivityRecord)
                .where(DeveloperActivityRecord.session_id == session_id.strip())
                .order_by(DeveloperActivityRecord.timestamp.asc())
            )
            records = session.scalars(stmt).all()
            return [
                DeveloperActivity(
                    event_id=r.event_id,
                    developer_id=r.developer_id,
                    project_path=r.project_path,
                    event_type=r.event_type,
                    timestamp=r.timestamp,
                    file_path=r.file_path,
                    session_id=r.session_id,
                    metadata=dict(r.metadata_json or {}),
                )
                for r in records
            ]

    def clear(self, developer_id: str | None = None) -> None:
        """Delete recorded activities, optionally filtered by developer ID."""
        with session_scope(self.session_factory) as session:
            stmt = delete(DeveloperActivityRecord)
            if developer_id:
                stmt = stmt.where(
                    DeveloperActivityRecord.developer_id == developer_id.strip()
                )
            session.execute(stmt)
