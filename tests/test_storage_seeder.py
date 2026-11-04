from prism.storage.repositories.memory_repo import (
    InMemorySkillGraphRepository,
)
from prism.storage.seeder import (
    DEFAULT_RELATIONSHIPS,
    DEFAULT_SKILLS,
    seed_default_curriculum,
)


def test_seed_default_curriculum() -> None:
    repo = InMemorySkillGraphRepository()
    seed_default_curriculum(repo)

    skills = repo.get_skills()
    assert len(skills) == len(DEFAULT_SKILLS)
    for _, skill_name, _ in DEFAULT_SKILLS:
        assert skill_name in skills

    rels = repo.get_relationships()
    assert len(rels) == len(DEFAULT_RELATIONSHIPS)


def test_seed_default_curriculum_idempotency() -> None:
    repo = InMemorySkillGraphRepository()

    # First run
    seed_default_curriculum(repo)
    first_skills_count = len(repo.get_skills())
    first_rels_count = len(repo.get_relationships())

    # Second run should not duplicate or error
    seed_default_curriculum(repo)
    assert len(repo.get_skills()) == first_skills_count
    assert len(repo.get_relationships()) == first_rels_count
