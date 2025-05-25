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
            importance=create_schema.importance,
            embedding=create_schema.embedding,
            create_iteration=create_schema.iteration,
            update_iteration=create_schema.iteration,
            last_accessed_iteration=create_schema.iteration,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)


async def update_long_term_memory(update_schema: LongTermMemoryUpdate) -> None:
    """Update a long-term memory with new content and importance."""
    async with db_sessionmaker() as session:
        query = (
            update(LongTermMemoryDBModel)
            .where(LongTermMemoryDBModel.id == update_schema.id)
            .values(
                content=update_schema.content,
                embedding=update_schema.embedding,
                importance=update_schema.importance,
                update_iteration=update_schema.iteration,
            )
        )
        await session.execute(query)
        await session.commit()


# TODO: Delete this when we have RAG set up.
async def get_all_long_term_memory(iteration: int) -> list[LongTermMemoryRead]:
    """Get all long-term memory."""
    async with db_sessionmaker() as session:
        query = (
            update(LongTermMemoryDBModel)
            .values(last_accessed_iteration=iteration)
            .returning(LongTermMemoryDBModel)
        )
        result = await session.execute(query)
        db_objs = result.scalars().all()

        return [LongTermMemoryRead.model_validate(o) for o in db_objs]


async def get_all_long_term_memory_titles() -> list[str]:
    """Get all long-term memory titles."""
    async with db_sessionmaker() as session:
        query = select(LongTermMemoryDBModel.title)
        result = await session.execute(query)
        db_objs = result.scalars().all()

        return list(db_objs)
