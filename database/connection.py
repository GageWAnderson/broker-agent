from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from broker_agent.config.settings import config


# Create SQLAlchemy engine with PostgreSQL connection from config
def get_database_url(async_mode: bool = False) -> str:
    """
    Constructs PostgreSQL database URL from configuration settings

    Args:
        async_mode: Whether to return an async-compatible URL

    Returns:
        str: Formatted database URL
    """
    prefix = "postgresql+asyncpg" if async_mode else "postgresql"
    return f"{prefix}://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"


# Create the engine with the configured URL
engine = create_engine(get_database_url())
async_engine = create_async_engine(get_database_url(async_mode=True))

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine
)

# Create a thread-local scoped session
ScopedSession = scoped_session(SessionLocal)


def get_db() -> Generator[Session, None, None]:
    """
    Creates a new database session for each request.
    Closes the session when the request is done.

    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a new async database session for each request.
    Closes the session when the request is done.

    Yields:
        AsyncSession: Async database session
    """
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Automatically handles commit/rollback and closing the session.

    Yields:
        Session: Database session
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    Automatically handles commit/rollback and closing the session.

    Yields:
        AsyncSession: Async database session
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_scoped_session() -> Session:
    """
    Returns the current scoped session or creates a new one.
    Use this for thread-local session management.

    Returns:
        Session: Scoped database session
    """
    return ScopedSession()


def remove_scoped_session() -> None:
    """
    Removes the current thread-local session.
    Should be called when the work with the session is done.
    """
    ScopedSession.remove()
