from sqlalchemy import select, update

from common.enums import MapId
from database.db_config import db_sessionmaker
from database.map_memory.model import MapMemoryDBModel
from database.map_memory.schemas import MapMemoryCreateUpdate, MapMemoryRead


async def create_map_memory(map_memory: MapMemoryCreateUpdate) -> MapMemoryRead:
    """Create a new map memory."""
    async with db_sessionmaker() as session:
        db_obj = MapMemoryDBModel(
            map_id=map_memory.map_id,
            tiles=map_memory.tiles,
            blockages=map_memory.blockages,
            create_iteration=map_memory.iteration,
            update_iteration=map_memory.iteration,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return MapMemoryRead.model_validate(db_obj)


async def get_map_memory(map_id: MapId) -> MapMemoryRead | None:
    """Get a map memory by map id."""
    async with db_sessionmaker() as session:
        query = select(MapMemoryDBModel).where(MapMemoryDBModel.map_id == map_id)
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            return None

    return MapMemoryRead.model_validate(db_obj)


async def update_map_tiles(map_memory: MapMemoryCreateUpdate) -> MapMemoryRead:
    """Update the tiles of a map memory."""
    async with db_sessionmaker() as session:
        query = (
            update(MapMemoryDBModel)
            .where(MapMemoryDBModel.map_id == map_memory.map_id)
            .values(
                tiles=map_memory.tiles,
                update_iteration=map_memory.iteration,
            )
            .returning(MapMemoryDBModel)
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(f"No map memory found for map_id {map_memory.map_id}")

        await session.commit()

        return MapMemoryRead.model_validate(db_obj)
