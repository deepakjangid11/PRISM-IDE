from prism.intelligence.models.skill_models import (
    RelationshipType,
    SkillRelationship,
)
from prism.logging.logger import get_logger
from prism.storage.repositories.base import SkillGraphRepository

logger = get_logger(__name__)

DEFAULT_SKILLS: list[tuple[str, str, str]] = [
    # (skill_id, canonical_name, category)
    ("skill_python", "Python", "language"),
    ("skill_sql", "SQL", "database"),
    ("skill_fastapi", "FastAPI", "framework"),
    ("skill_numpy", "NumPy", "library"),
    ("skill_pandas", "Pandas", "library"),
    ("skill_statistics", "Statistics", "math"),
    ("skill_ml", "Machine Learning", "domain"),
    ("skill_oop", "Object-Oriented Programming", "paradigm"),
    ("skill_ds", "Data Structures", "fundamentals"),
    ("skill_algo", "Algorithms", "fundamentals"),
    ("skill_arch", "Software Architecture", "architecture"),
    ("skill_html_css", "HTML/CSS", "frontend"),
    ("skill_js", "JavaScript", "language"),
    ("skill_ts", "TypeScript", "language"),
    ("skill_react", "React", "frontend"),
    ("skill_flutter", "Flutter", "frontend"),
    ("skill_rest", "REST APIs", "architecture"),
    ("skill_db_design", "Database Design", "database"),
    ("skill_testing", "Testing", "quality"),
    ("skill_data_validation", "Data Validation", "quality"),
]

DEFAULT_RELATIONSHIPS: list[tuple[str, str, RelationshipType]] = [
    # Machine Learning pathway
    ("Python", "NumPy", RelationshipType.PREREQUISITE),
    ("NumPy", "Pandas", RelationshipType.PREREQUISITE),
    ("Python", "Statistics", RelationshipType.PREREQUISITE),
    ("Pandas", "Machine Learning", RelationshipType.PREREQUISITE),
    ("Statistics", "Machine Learning", RelationshipType.PREREQUISITE),
    # Backend & Architecture pathway
    ("Python", "FastAPI", RelationshipType.PREREQUISITE),
    ("FastAPI", "REST APIs", RelationshipType.PREREQUISITE),
    ("SQL", "Database Design", RelationshipType.PREREQUISITE),
    ("Database Design", "Software Architecture", RelationshipType.PREREQUISITE),
    ("REST APIs", "Software Architecture", RelationshipType.PREREQUISITE),
    ("Python", "Object-Oriented Programming", RelationshipType.PREREQUISITE),
    (
        "Object-Oriented Programming",
        "Software Architecture",
        RelationshipType.PREREQUISITE,
    ),
    ("Data Structures", "Algorithms", RelationshipType.PREREQUISITE),
    ("Algorithms", "Software Architecture", RelationshipType.PREREQUISITE),
    # Frontend pathway
    ("HTML/CSS", "JavaScript", RelationshipType.PREREQUISITE),
    ("JavaScript", "TypeScript", RelationshipType.PREREQUISITE),
    ("TypeScript", "React", RelationshipType.PREREQUISITE),
    (
        "Object-Oriented Programming",
        "Flutter",
        RelationshipType.PREREQUISITE,
    ),
    # Related links
    ("FastAPI", "REST APIs", RelationshipType.RELATED),
    ("React", "Flutter", RelationshipType.RELATED),
    ("Machine Learning", "Statistics", RelationshipType.RELATED),
]


def seed_default_curriculum(graph_repo: SkillGraphRepository) -> None:
    """Idempotently seed the default software engineering skill curriculum."""
    logger.info("Starting default skill curriculum seeding")

    # 1. Register canonical skills
    for skill_id, skill_name, category in DEFAULT_SKILLS:
        graph_repo.register_skill(skill_id, skill_name, category)

    # 2. Add relationships
    for from_skill, to_skill, rel_type in DEFAULT_RELATIONSHIPS:
        graph_repo.add_relationship(
            SkillRelationship(
                from_skill=from_skill,
                to_skill=to_skill,
                relationship_type=rel_type,
            )
        )

    logger.info(
        "Default skill curriculum seeded successfully | skills=%d | edges=%d",
        len(DEFAULT_SKILLS),
        len(DEFAULT_RELATIONSHIPS),
    )


if __name__ == "__main__":
    from prism.storage.database import get_session_factory
    from prism.storage.repositories.mysql_graph_repo import (
        MySQLSkillGraphRepository,
    )

    factory = get_session_factory()
    repository = MySQLSkillGraphRepository(factory)
    seed_default_curriculum(repository)
    print(
        f"Seeded curriculum: {len(DEFAULT_SKILLS)} skills, "
        f"{len(DEFAULT_RELATIONSHIPS)} relationships."
    )
