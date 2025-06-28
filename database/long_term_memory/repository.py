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


async def get_long_term_memories(
    titles: list[str],
    iteration: int,
) -> list[LongTermMemoryRead]:
    """Get long-term memories by their titles."""
    async with db_sessionmaker() as session:
        query = (
            update(LongTermMemoryDBModel)
            .where(LongTermMemoryDBModel.title.in_(titles))
            .values(last_accessed_iteration=iteration)
            .returning(LongTermMemoryDBModel)
        )
        result = await session.execute(query)
        db_objs = result.scalars().all()
        await session.commit()

        return [LongTermMemoryRead.model_validate(o) for o in db_objs]


async def update_long_term_memory(update_schema: LongTermMemoryUpdate) -> None:
    """Update a long-term memory with new content and importance."""
    async with db_sessionmaker() as session:
        query = (
            update(LongTermMemoryDBModel)
            .where(LongTermMemoryDBModel.title == update_schema.title)
            .values(
                content=update_schema.content,
                embedding=update_schema.embedding,
                importance=update_schema.importance,
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


async def get_all_long_term_memory_embeddings() -> dict[str, list[float]]:
    """Get all long-term memory embeddings."""
    async with db_sessionmaker() as session:
        query = select(LongTermMemoryDBModel.title, LongTermMemoryDBModel.embedding)
        result = await session.execute(query)
        db_objs = result.all()

        return {o[0]: o[1] for o in db_objs}
