from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from common.constants import DB_FILE_PATH, DB_URL
from database.base import SQLAlchemyBase

_engine = create_async_engine(
    DB_URL,
    echo=True,
    connect_args={"check_same_thread": False},
)
_sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    async with _sessionmaker() as session:
        yield session


async def init_fresh_db() -> None:
    """Initialize a fresh database by dropping all existing tables and recreating them."""
    logger.info(f"Initializing a fresh database at: {DB_URL}")

    # These are the tables that will be created in the database.

    async with _engine.begin() as conn:
        if DB_FILE_PATH.exists():
            await conn.run_sync(SQLAlchemyBase.metadata.drop_all)

        await conn.run_sync(SQLAlchemyBase.metadata.create_all)

        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous = NORMAL"))

    logger.info("Database initialized successfully.")
