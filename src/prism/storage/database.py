import sys
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from prism.config.settings import settings
from prism.exceptions.custom_exception import CustomException
from prism.logging.logger import get_logger

logger = get_logger(__name__)


def create_db_engine(
    database_url: str | None = None,
    echo: bool | None = None,
) -> Engine:
    """Create SQLAlchemy engine with connection pooling and health checks."""
    url = database_url or settings.database_url
    is_echo = echo if echo is not None else settings.db_echo

    logger.info("Initializing database engine with pool recycling")
    return create_engine(
        url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
        echo=is_echo,
    )


# Lazily created engine and session factory
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return active database engine, instantiating if needed."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return configured session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


@contextmanager
def session_scope(
    factory: sessionmaker[Session] | None = None,
) -> Generator[Session]:
    """Provide a transactional scope around a series of operations with automatic rollback."""
    sm = factory or get_session_factory()
    session = sm()
    try:
        yield session
        session.commit()
    except Exception as error:
        session.rollback()
        logger.error("Transaction failed and was rolled back: %s", error)
        raise CustomException(error, sys) from error
    finally:
        session.close()


def get_db() -> Generator[Session]:
    """FastAPI dependency for per-request database sessions."""
    sm = get_session_factory()
    session = sm()
    try:
        yield session
        session.commit()
    except Exception as error:
        session.rollback()
        logger.error("Request session rolled back due to error: %s", error)
        raise
    finally:
        session.close()
