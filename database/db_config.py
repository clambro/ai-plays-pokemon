from collections.abc import AsyncGenerator
from pathlib import Path

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database.base import SQLAlchemyBase


def get_db_path(folder: Path) -> str:
    """Get the database path for a specific folder."""
    db_path = folder / "memory.db"
    return f"sqlite+aiosqlite:///{db_path}"


def create_engine_for_folder(folder: Path) -> AsyncEngine:
    """Create a database engine for a specific agent folder."""
    db_path = get_db_path(folder)
    logger.info(f"Creating database engine for path: {db_path}")

    engine = create_async_engine(
        db_path,
        echo=True,
        connect_args={"check_same_thread": False},
    )
    return engine


def create_session_maker_for_folder(folder: Path) -> async_sessionmaker:
    """Create a session maker for a specific agent folder."""
    engine = create_engine_for_folder(folder)
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(folder: Path) -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for a specific agent folder."""
    session_maker = create_session_maker_for_folder(folder)
    async with session_maker() as session:
        yield session


async def init_db(folder: Path) -> None:
    """Initialize the database for a specific agent folder."""
    db_path = get_db_path(folder)
    logger.info(f"Initializing database. Full path: {db_path}")

    # These are the tables that will be created in the database.

    engine = create_engine_for_folder(folder)
    async with engine.begin() as conn:
        await conn.run_sync(SQLAlchemyBase.metadata.create_all)

        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous = NORMAL"))

    logger.info("Database initialized successfully")
