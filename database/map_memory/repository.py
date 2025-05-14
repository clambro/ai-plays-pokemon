from sqlalchemy import select, update

from database.db_config import db_sessionmaker
from database.map_memory.model import MapMemoryDBModel
from database.map_memory.schemas import MapMemory


async def create_map_memory(map_memory: MapMemory) -> MapMemory:
    """Create a new map memory."""
    async with db_sessionmaker() as session:
        db_obj = MapMemoryDBModel(map_id=map_memory.map_id, tiles=map_memory.tiles)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return MapMemory.model_validate(db_obj)


async def get_map_memory(map_id: int) -> MapMemory | None:
    """Get a map memory by map id."""
    async with db_sessionmaker() as session:
        query = select(MapMemoryDBModel).where(MapMemoryDBModel.map_id == map_id)
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            return None

    return MapMemory.model_validate(db_obj)


async def update_map_tiles(map_memory: MapMemory) -> MapMemory:
    """Update the tiles of a map memory."""
    async with db_sessionmaker() as session:
        query = (
            update(MapMemoryDBModel)
            .where(MapMemoryDBModel.map_id == map_memory.map_id.value)
            .values(tiles=map_memory.tiles)
            .returning(MapMemoryDBModel)
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(f"No map memory found for map_id {map_memory.map_id}")

        await session.commit()

        return MapMemory.model_validate(db_obj)
