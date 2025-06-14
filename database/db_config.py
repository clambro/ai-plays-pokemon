# ruff: noqa: F401

import aiofiles.os
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
    """Initialize a fresh database by deleting the database folder and recreating it."""
    logger.info(f"Initializing a fresh database at: {DB_URL}")

    db_folder = DB_FILE_PATH.parent
    if db_folder.exists():
        for file in db_folder.iterdir():
            if file.is_file():
                await aiofiles.os.remove(file)
        await aiofiles.os.rmdir(db_folder)
    await aiofiles.os.makedirs(db_folder)

    # Import all models here to ensure they are registered with the engine.
    from database.llm_messages.model import LLMMessageDBModel
    from database.long_term_memory.model import LongTermMemoryDBModel
    from database.map_entity_memory.model import MapEntityMemoryDBModel
    from database.map_memory.model import MapMemoryDBModel

    async with _engine.begin() as conn:
        await conn.run_sync(SQLAlchemyBase.metadata.create_all)

        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous = NORMAL"))

    logger.info("Database initialized successfully.")
