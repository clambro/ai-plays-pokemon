# ruff: noqa: F401

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.constants import DB_FILE_PATH, DB_URL
from database.base import SQLAlchemyBase

_engine = create_async_engine(
    DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
db_sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)


async def init_fresh_db() -> None:
    """Initialize a fresh database by dropping all existing tables and recreating them."""
    logger.info(f"Initializing a fresh database at: {DB_URL}")

    # Import all models here to ensure they are registered with the engine.
    from database.llm_messages.model import LLMMessageDBModel
    from database.long_term_memory.model import LongTermMemoryDBModel
    from database.map_entity_memory.model import MapEntityMemoryDBModel
    from database.map_memory.model import MapMemoryDBModel
    from database.sprite_memory.model import SpriteMemoryDBModel
    from database.warp_memory.model import WarpMemoryDBModel

    async with _engine.begin() as conn:
        if DB_FILE_PATH.exists():
            await conn.run_sync(SQLAlchemyBase.metadata.drop_all)

        await conn.run_sync(SQLAlchemyBase.metadata.create_all)

        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous = NORMAL"))

    logger.info("Database initialized successfully.")
