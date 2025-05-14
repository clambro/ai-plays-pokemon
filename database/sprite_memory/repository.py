from sqlalchemy import select, update

from database.db_config import db_sessionmaker
from database.sprite_memory.model import SpriteMemoryTable
from database.sprite_memory.schemas import SpriteMemory


async def create_sprite_memory(sprite: SpriteMemory) -> SpriteMemory:
    """Create a new sprite memory."""
    async with db_sessionmaker() as session:
        db_obj = SpriteMemoryTable(
            map_id=sprite.map_id,
            sprite_id=sprite.sprite_id,
            description=sprite.description,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return SpriteMemory.model_validate(db_obj)


async def get_sprite_memory(map_id: int, sprite_id: int) -> SpriteMemory:
    """Get a sprite memory by map id and sprite id."""
    async with db_sessionmaker() as session:
        query = select(SpriteMemoryTable).where(
            SpriteMemoryTable.map_id == map_id,
            SpriteMemoryTable.sprite_id == sprite_id,
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(
                f"No sprite memory found for map_id: {map_id} and sprite_id: {sprite_id}",
            )

    return SpriteMemory.model_validate(db_obj)


async def update_known_sprite_description(sprite: SpriteMemory) -> SpriteMemory:
    """Update the description of a sprite memory."""
    async with db_sessionmaker() as session:
        query = (
            update(SpriteMemoryTable)
            .where(
                SpriteMemoryTable.map_id == sprite.map_id,
                SpriteMemoryTable.sprite_id == sprite.sprite_id,
            )
            .values(description=sprite.description)
            .returning(SpriteMemoryTable)
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
