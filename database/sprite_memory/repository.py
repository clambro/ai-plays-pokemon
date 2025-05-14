from sqlalchemy import delete, select, update

from database.db_config import db_sessionmaker
from database.sprite_memory.model import SpriteMemoryDBModel
from database.sprite_memory.schemas import SpriteMemory


async def create_sprite_memory(sprite: SpriteMemory) -> SpriteMemory:
    """Create a new sprite memory."""
    async with db_sessionmaker() as session:
        db_obj = SpriteMemoryDBModel(
            map_id=sprite.map_id,
            sprite_id=sprite.sprite_id,
            description=sprite.description,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return SpriteMemory.model_validate(db_obj)


async def get_sprite_memories_for_map(map_id: int) -> list[SpriteMemory]:
    """Get all sprite memories for a map."""
    async with db_sessionmaker() as session:
        query = select(SpriteMemoryDBModel).where(SpriteMemoryDBModel.map_id == map_id)
        result = await session.execute(query)
        db_objs = result.scalars().all()

    return [SpriteMemory.model_validate(d) for d in db_objs]


async def update_known_sprite_description(sprite: SpriteMemory) -> SpriteMemory:
    """Update the description of a sprite memory."""
    async with db_sessionmaker() as session:
        query = (
            update(SpriteMemoryDBModel)
            .where(
                SpriteMemoryDBModel.map_id == sprite.map_id,
                SpriteMemoryDBModel.sprite_id == sprite.sprite_id,
            )
            .values(description=sprite.description)
            .returning(SpriteMemoryDBModel)
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(
                f"No sprite memory found for map_id: {sprite.map_id}"
                f" and sprite_id: {sprite.sprite_id}",
            )

        await session.commit()
    return SpriteMemory.model_validate(db_obj)


async def delete_sprite_memory(map_id: int, sprite_id: int) -> None:
    """Delete a sprite memory."""
    async with db_sessionmaker() as session:
        query = delete(SpriteMemoryDBModel).where(
            SpriteMemoryDBModel.map_id == map_id,
            SpriteMemoryDBModel.sprite_id == sprite_id,
        )
        await session.execute(query)
        await session.commit()
