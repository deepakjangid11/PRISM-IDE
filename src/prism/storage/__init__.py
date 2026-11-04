from typing import TYPE_CHECKING, Any

from prism.storage.bootstrap import check_db_connection
from prism.storage.database import (
    create_db_engine,
    get_db,
    get_engine,
    get_session_factory,
    session_scope,
)
from prism.storage.models.base import Base

if TYPE_CHECKING:
    from prism.storage.seeder import seed_default_curriculum

__all__ = [
    "Base",
    "check_db_connection",
    "create_db_engine",
    "get_db",
    "get_engine",
    "get_session_factory",
    "seed_default_curriculum",
    "session_scope",
]


def __getattr__(name: str) -> Any:
    if name == "seed_default_curriculum":
        from prism.storage.seeder import seed_default_curriculum

        return seed_default_curriculum
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
