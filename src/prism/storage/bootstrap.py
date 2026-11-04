from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from prism.logging.logger import get_logger
from prism.storage.database import get_engine
from prism.storage.models.base import Base

logger = get_logger(__name__)


def check_db_connection(engine: Engine | None = None) -> bool:
    """Verify database connectivity via a ping query."""
    eng = engine or get_engine()
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connectivity verified")
        return True
    except (SQLAlchemyError, OSError) as err:
        logger.warning("Database connectivity check failed: %s", err)
        return False


def create_schema_for_test(engine: Engine) -> None:
    """Explicitly create tables in a dedicated test database (never for production)."""
    logger.info("Creating schema in dedicated test database")
    Base.metadata.create_all(bind=engine)


def drop_schema_for_test(engine: Engine) -> None:
    """Drop tables in dedicated test database."""
    logger.info("Dropping schema in dedicated test database")
    Base.metadata.drop_all(bind=engine)
