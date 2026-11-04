from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from prism.intelligence.models.skill_models import (
    RelationshipType,
    SkillRelationship,
)
from prism.storage.database import session_scope
from prism.storage.models.skill_records import (
    SkillRecord,
    SkillRelationshipRecord,
)


class MySQLSkillGraphRepository:
    """MySQL-backed repository for technical skills and relationship topology."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def register_skill(
        self, skill_id: str, skill_name: str, category: str | None = None
    ) -> str:
        """Register a technical skill, returning its stable surrogate skill_id."""
        canonical = skill_name.strip()
        cleaned_id = skill_id.strip()

        with session_scope(self.session_factory) as session:
            # Check by skill_name
            stmt = select(SkillRecord).where(SkillRecord.skill_name == canonical)
            existing = session.scalar(stmt)
            if existing is not None:
                return existing.skill_id

            record = SkillRecord(
                skill_id=cleaned_id,
                skill_name=canonical,
                category=category,
                created_at=datetime.now(UTC),
            )
            session.add(record)
            return cleaned_id

    def get_skill_id_by_name(self, skill_name: str) -> str | None:
        """Resolve a canonical skill name to its surrogate skill_id."""
        with session_scope(self.session_factory) as session:
            stmt = select(SkillRecord.skill_id).where(
                SkillRecord.skill_name == skill_name.strip()
            )
            return session.scalar(stmt)

    def get_skill_name_by_id(self, skill_id: str) -> str | None:
        """Resolve a surrogate skill_id to its canonical skill name."""
        with session_scope(self.session_factory) as session:
            stmt = select(SkillRecord.skill_name).where(
                SkillRecord.skill_id == skill_id.strip()
            )
            return session.scalar(stmt)

    def add_relationship(self, relationship: SkillRelationship) -> None:
        """Add a directed relationship between skills."""
        from_id = self.get_skill_id_by_name(relationship.from_skill)
        to_id = self.get_skill_id_by_name(relationship.to_skill)

        if not from_id:
            from_id = f"skill_{relationship.from_skill.lower().replace(' ', '_').replace('/', '_')}"
            self.register_skill(from_id, relationship.from_skill)

        if not to_id:
            to_id = f"skill_{relationship.to_skill.lower().replace(' ', '_').replace('/', '_')}"
            self.register_skill(to_id, relationship.to_skill)

        with session_scope(self.session_factory) as session:
            stmt = select(SkillRelationshipRecord).where(
                SkillRelationshipRecord.from_skill_id == from_id,
                SkillRelationshipRecord.to_skill_id == to_id,
                SkillRelationshipRecord.relationship_type
                == relationship.relationship_type.value,
            )
            existing = session.scalar(stmt)
            if existing is None:
                rel_record = SkillRelationshipRecord(
                    from_skill_id=from_id,
                    to_skill_id=to_id,
                    relationship_type=relationship.relationship_type.value,
                    created_at=datetime.now(UTC),
                )
                session.add(rel_record)

    def get_skills(self) -> list[str]:
        """Return all registered canonical skill names."""
        with session_scope(self.session_factory) as session:
            stmt = select(SkillRecord.skill_name).order_by(SkillRecord.skill_name)
            return list(session.scalars(stmt).all())

    def get_relationships(self) -> list[SkillRelationship]:
        """Return all directed skill relationships mapped to domain models."""
        from sqlalchemy.orm import aliased

        with session_scope(self.session_factory) as session:
            from_skill_alias = aliased(SkillRecord)
            to_skill_alias = aliased(SkillRecord)

            stmt = (
                select(
                    from_skill_alias.skill_name.label("from_name"),
                    to_skill_alias.skill_name.label("to_name"),
                    SkillRelationshipRecord.relationship_type,
                )
                .join(
                    from_skill_alias,
                    SkillRelationshipRecord.from_skill_id == from_skill_alias.skill_id,
                )
                .join(
                    to_skill_alias,
                    SkillRelationshipRecord.to_skill_id == to_skill_alias.skill_id,
                )
                .order_by(
                    from_skill_alias.skill_name.asc(),
                    to_skill_alias.skill_name.asc(),
                )
            )
            rows = session.execute(stmt).all()
            return [
                SkillRelationship(
                    from_skill=row.from_name,
                    to_skill=row.to_name,
                    relationship_type=RelationshipType(row.relationship_type),
                )
                for row in rows
            ]
