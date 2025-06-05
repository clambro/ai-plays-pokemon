from sqlalchemy import delete, select, update

from database.db_config import db_sessionmaker
from database.map_entity_memory.model import MapEntityMemoryDBModel
from database.map_entity_memory.schemas import (
    MapEntityMemoryCreate,
    MapEntityMemoryDelete,
    MapEntityMemoryRead,
    MapEntityMemoryUpdate,
)


async def create_map_entity_memory(map_entity: MapEntityMemoryCreate) -> MapEntityMemoryRead:
    """Create a new warp memory."""
    async with db_sessionmaker() as session:
        db_obj = MapEntityMemoryDBModel(
            map_id=map_entity.map_id,
            entity_id=map_entity.entity_id,
            entity_type=map_entity.entity_type,
            description=None,
            create_iteration=map_entity.iteration,
            update_iteration=map_entity.iteration,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return MapEntityMemoryRead.model_validate(db_obj)


async def get_map_entity_memories_for_map(map_id: int) -> list[MapEntityMemoryRead]:
    """Get all map entity memories for a map."""
    async with db_sessionmaker() as session:
        query = select(MapEntityMemoryDBModel).where(MapEntityMemoryDBModel.map_id == map_id)
        result = await session.execute(query)
        db_objs = result.scalars().all()

    return [MapEntityMemoryRead.model_validate(d) for d in db_objs]


async def update_map_entity_memory(map_entity: MapEntityMemoryUpdate) -> MapEntityMemoryRead:
    """Update the description of a map entity memory."""
    async with db_sessionmaker() as session:
        query = (
            update(MapEntityMemoryDBModel)
            .where(
                MapEntityMemoryDBModel.map_id == map_entity.map_id,
                MapEntityMemoryDBModel.entity_id == map_entity.entity_id,
                MapEntityMemoryDBModel.entity_type == map_entity.entity_type,
            )
            .values(
                description=map_entity.description,
                update_iteration=map_entity.iteration,
            )
            .returning(MapEntityMemoryDBModel)
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(
                f"No map entity memory found for map_id: {map_entity.map_id}"
                f" and entity_id: {map_entity.entity_id}"
                f" and entity_type: {map_entity.entity_type}",
            )

        await session.commit()

        return MapEntityMemoryRead.model_validate(db_obj)


async def delete_map_entity_memory(map_entity: MapEntityMemoryDelete) -> None:
    """Delete a map entity memory."""
    async with db_sessionmaker() as session:
        query = delete(MapEntityMemoryDBModel).where(
            MapEntityMemoryDBModel.map_id == map_entity.map_id,
            MapEntityMemoryDBModel.entity_id == map_entity.entity_id,
            MapEntityMemoryDBModel.entity_type == map_entity.entity_type,
        )
        await session.execute(query)
        await session.commit()
