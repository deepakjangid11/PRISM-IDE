from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    DeveloperSkillProfile,
    ProficiencyLevel,
    SkillEvidence,
)
from prism.storage.database import session_scope
from prism.storage.models.skill_records import (
    DeveloperSkillRecord,
    SkillEvidenceRecord,
)
from prism.storage.repositories.mysql_developer_repo import (
    MySQLDeveloperRepository,
)
from prism.storage.repositories.mysql_graph_repo import (
    MySQLSkillGraphRepository,
)


class MySQLSkillRepository:
    """MySQL-backed repository for skill evidence and developer assessments."""

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

    def record_evidence(self, evidence: SkillEvidence) -> None:
        """Store verifiable skill evidence linked to developer and skill."""
        dev_id = evidence.developer_id.strip()
        self.developer_repo.ensure_developer(dev_id)

        skill_id = self.graph_repo.get_skill_id_by_name(evidence.skill_name)
        if not skill_id:
            slug = evidence.skill_name.lower().replace(" ", "_").replace("/", "_")
            skill_id = f"skill_{slug}"
            self.graph_repo.register_skill(skill_id, evidence.skill_name)

        with session_scope(self.session_factory) as session:
            record = SkillEvidenceRecord(
                evidence_id=evidence.evidence_id,
                developer_id=dev_id,
                skill_id=skill_id,
                evidence_type=evidence.evidence_type,
                description=evidence.description,
                timestamp=evidence.timestamp,
                project_path=evidence.project_path,
                metadata_json=dict(evidence.metadata),
            )
            session.merge(record)

    def get_evidence(
        self, developer_id: str, skill_name: str | None = None
    ) -> list[SkillEvidence]:
        """Fetch evidence for a developer, optionally filtered by skill."""
        dev_id = developer_id.strip()
        skill_id = (
            self.graph_repo.get_skill_id_by_name(skill_name) if skill_name else None
        )

        with session_scope(self.session_factory) as session:
            stmt = select(SkillEvidenceRecord).where(
                SkillEvidenceRecord.developer_id == dev_id
            )
            if skill_id:
                stmt = stmt.where(SkillEvidenceRecord.skill_id == skill_id)
            stmt = stmt.order_by(SkillEvidenceRecord.timestamp.asc())

            records = session.scalars(stmt).all()
            evidence_items: list[SkillEvidence] = []
            for r in records:
                s_name = self.graph_repo.get_skill_name_by_id(r.skill_id) or r.skill_id
                evidence_items.append(
                    SkillEvidence(
                        evidence_id=r.evidence_id,
                        developer_id=r.developer_id,
                        skill_name=s_name,
                        evidence_type=r.evidence_type,
                        description=r.description,
                        timestamp=r.timestamp,
                        project_path=r.project_path,
                        metadata=dict(r.metadata_json or {}),
                    )
                )
            return evidence_items

    def save_skill_assessment(self, skill: DeveloperSkill) -> None:
        """Persist materialized developer skill assessment."""
        dev_id = skill.developer_id.strip()
        self.developer_repo.ensure_developer(dev_id)

        skill_id = self.graph_repo.get_skill_id_by_name(skill.skill_name)
        if not skill_id:
            slug = skill.skill_name.lower().replace(" ", "_").replace("/", "_")
            skill_id = f"skill_{slug}"
            self.graph_repo.register_skill(skill_id, skill.skill_name)

        with session_scope(self.session_factory) as session:
            stmt = select(DeveloperSkillRecord).where(
                DeveloperSkillRecord.developer_id == dev_id,
                DeveloperSkillRecord.skill_id == skill_id,
            )
            existing = session.scalar(stmt)
            if existing is None:
                record = DeveloperSkillRecord(
                    developer_id=dev_id,
                    skill_id=skill_id,
                    proficiency_level=skill.proficiency_level.value,
                    evidence_count=skill.evidence_count,
                    has_sufficient_evidence=skill.has_sufficient_evidence,
                    last_assessed=skill.last_assessed or datetime.now(UTC),
                )
                session.add(record)
            else:
                existing.proficiency_level = skill.proficiency_level.value
                existing.evidence_count = skill.evidence_count
                existing.has_sufficient_evidence = skill.has_sufficient_evidence
                existing.last_assessed = skill.last_assessed or datetime.now(UTC)

    def get_profile(self, developer_id: str) -> DeveloperSkillProfile:
        """Fetch developer skill profile with evidence collections."""
        dev_id = developer_id.strip()
        self.developer_repo.ensure_developer(dev_id)

        with session_scope(self.session_factory) as session:
            stmt = select(DeveloperSkillRecord).where(
                DeveloperSkillRecord.developer_id == dev_id
            )
            records = session.scalars(stmt).all()

            skills_dict: dict[str, DeveloperSkill] = {}
            for r in records:
                s_name = self.graph_repo.get_skill_name_by_id(r.skill_id) or r.skill_id
                # Fetch evidence for this specific skill
                evidence_list = self.get_evidence(dev_id, s_name)
                skills_dict[s_name.lower()] = DeveloperSkill(
                    developer_id=dev_id,
                    skill_name=s_name,
                    proficiency_level=ProficiencyLevel(r.proficiency_level),
                    evidence_count=r.evidence_count,
                    evidence_list=evidence_list,
                    has_sufficient_evidence=r.has_sufficient_evidence,
                    last_assessed=r.last_assessed,
                )

            return DeveloperSkillProfile(
                developer_id=dev_id,
                skills=skills_dict,
                last_updated=datetime.now(UTC),
            )

    def list_developers(self) -> list[str]:
        """Return list of all registered developer IDs."""
        return self.developer_repo.list_developers()
