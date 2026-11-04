from sqlalchemy.dialects.mysql import DATETIME

from prism.storage.models.base import Base


def test_registered_tables_count_and_names() -> None:
    tables = Base.metadata.tables
    expected_tables = {
        "developers",
        "skills",
        "skill_relationships",
        "developer_activities",
        "skill_evidence",
        "developer_skills",
        "learning_progress",
        "learning_progress_items",
        "learning_progress_history",
    }
    assert expected_tables.issubset(set(tables.keys()))


def test_developers_table_schema() -> None:
    table = Base.metadata.tables["developers"]
    cols = table.columns
    assert "developer_id" in cols
    assert cols["developer_id"].primary_key is True
    assert "name" in cols
    assert "email" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    assert isinstance(cols["created_at"].type, DATETIME)
    assert cols["created_at"].type.fsp == 6


def test_skills_table_schema() -> None:
    table = Base.metadata.tables["skills"]
    cols = table.columns
    assert "skill_id" in cols
    assert cols["skill_id"].primary_key is True
    assert "skill_name" in cols
    assert cols["skill_name"].unique is True
    assert "category" in cols
    assert isinstance(cols["created_at"].type, DATETIME)
    assert cols["created_at"].type.fsp == 6


def test_foreign_keys_and_cascades() -> None:
    tables = Base.metadata.tables

    # Activity references developers with cascade
    act_table = tables["developer_activities"]
    dev_fk = next(fk for fk in act_table.foreign_keys)
    assert dev_fk.column.table.name == "developers"
    assert dev_fk.ondelete == "CASCADE"

    # Skill relationship references skills twice with cascade
    rel_table = tables["skill_relationships"]
    assert len(rel_table.foreign_keys) == 2
    for fk in rel_table.foreign_keys:
        assert fk.column.table.name == "skills"
        assert fk.ondelete == "CASCADE"

    # Skill evidence references both developer and skill
    ev_table = tables["skill_evidence"]
    fk_tables = {fk.column.table.name for fk in ev_table.foreign_keys}
    assert fk_tables == {"developers", "skills"}
    for fk in ev_table.foreign_keys:
        assert fk.ondelete == "CASCADE"

    # Learning progress items references learning_progress and skills
    item_table = tables["learning_progress_items"]
    fk_targets = {fk.column.table.name for fk in item_table.foreign_keys}
    assert fk_targets == {"learning_progress", "skills"}


def test_unique_constraints() -> None:
    tables = Base.metadata.tables

    rel_table = tables["skill_relationships"]
    rel_uqs = [
        c.name
        for c in rel_table.constraints
        if getattr(c, "name", None) == "uq_skill_rel_edge"
    ]
    assert "uq_skill_rel_edge" in rel_uqs

    dev_skill_table = tables["developer_skills"]
    skill_uqs = [
        c.name
        for c in dev_skill_table.constraints
        if getattr(c, "name", None) == "uq_dev_skill_pair"
    ]
    assert "uq_dev_skill_pair" in skill_uqs

    prog_table = tables["learning_progress"]
    prog_uqs = [
        c.name
        for c in prog_table.constraints
        if getattr(c, "name", None) == "uq_learning_dev_goal"
    ]
    assert "uq_learning_dev_goal" in prog_uqs
