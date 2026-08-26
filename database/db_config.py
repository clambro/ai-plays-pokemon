"""Database engine and session configuration."""

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
    db_folder = DB_FILE_PATH.parent
    if db_folder.exists():
        for file in db_folder.iterdir():
            if file.is_file():
                await aiofiles.os.remove(file)
        await aiofiles.os.rmdir(db_folder)
    await aiofiles.os.makedirs(db_folder)

    # Import all models here to ensure they are registered with the engine.
    from database.map_entity_memory.model import (  # noqa: F401, PLC0415
        MapEntityMemoryDBModel,
    )
    from database.map_memory.model import MapMemoryDBModel  # noqa: F401, PLC0415
    from database.rolling_memory.model import (  # noqa: F401, PLC0415
        MemorySummaryDBModel,
        RawMemoryBlockDBModel,
    )

    async with _engine.begin() as conn:
        await conn.run_sync(SQLAlchemyBase.metadata.create_all)

        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous = NORMAL"))

    logger.info("Initialized fresh database at {}.", DB_FILE_PATH)
