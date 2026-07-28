"""Persistence operations for long term memory."""

from sqlalchemy import select, update

from database.db_config import db_sessionmaker
from database.long_term_memory.model import LongTermMemoryDBModel
from database.long_term_memory.schemas import (
    LongTermMemoryCreate,
    LongTermMemoryRead,
    LongTermMemoryUpdate,
)


async def create_long_term_memory(create_schema: LongTermMemoryCreate) -> None:
    """Create a new long-term memory. No need to return it because it's not used this way."""
    async with db_sessionmaker() as session:
        db_obj = LongTermMemoryDBModel(
            title=create_schema.title,
            content=create_schema.content,
            create_iteration=create_schema.iteration,
            update_iteration=create_schema.iteration,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)


async def get_long_term_memories(
    titles: list[str],
) -> list[LongTermMemoryRead]:
    """Get long-term memories by title.

    Args:
        titles: Memory titles to retrieve.

    Returns:
        Matching memories.
    """
    async with db_sessionmaker() as session:
        query = select(LongTermMemoryDBModel).where(LongTermMemoryDBModel.title.in_(titles))
        result = await session.execute(query)
        db_objs = result.scalars().all()

        return [LongTermMemoryRead.model_validate(o) for o in db_objs]


async def update_long_term_memory(update_schema: LongTermMemoryUpdate) -> None:
    """Update a long-term memory with new content."""
    async with db_sessionmaker() as session:
        query = (
            update(LongTermMemoryDBModel)
            .where(LongTermMemoryDBModel.title == update_schema.title)
            .values(
                content=update_schema.content,
                update_iteration=update_schema.iteration,
            )
        )
        await session.execute(query)
        await session.commit()


async def get_all_long_term_memory_titles() -> list[str]:
    """Get all long-term memory titles."""
    async with db_sessionmaker() as session:
        query = select(LongTermMemoryDBModel.title)
        result = await session.execute(query)
        db_objs = result.scalars().all()

        return list(db_objs)
