"""Persistence operations for map entity memory."""

from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import and_, delete, or_, select

from database.db_config import db_sessionmaker
from database.map_entity_memory.model import MapEntityMemoryDBModel
from database.map_entity_memory.schemas import (
    MapEntityMemoryCreate,
    MapEntityMemoryDelete,
    MapEntityMemoryInteractionUpdate,
    MapEntityMemoryRead,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from common.enums import MapId


async def get_map_entity_memories_for_map(map_id: MapId) -> list[MapEntityMemoryRead]:
    """Get all map entity memories for a map."""
    async with db_sessionmaker() as session:
        query = select(MapEntityMemoryDBModel).where(MapEntityMemoryDBModel.map_id == map_id)
        result = await session.execute(query)
        db_objs = result.scalars().all()

    return [MapEntityMemoryRead.model_validate(d) for d in db_objs]


async def apply_map_entity_changes(
    *,
    creates: Sequence[MapEntityMemoryCreate] = (),
    deletes: Sequence[MapEntityMemoryDelete] = (),
) -> None:
    """Apply a batch of map-entity changes in one transaction."""
    if not creates and not deletes:
        return

    async with db_sessionmaker.begin() as session:
        session.add_all(
            [
                MapEntityMemoryDBModel(
                    map_id=entity.map_id,
                    entity_id=entity.entity_id,
                    entity_type=entity.entity_type,
                )
                for entity in creates
            ],
        )

        if deletes:
            await session.execute(
                delete(MapEntityMemoryDBModel).where(
                    or_(
                        *[
                            and_(
                                MapEntityMemoryDBModel.map_id == entity.map_id,
                                MapEntityMemoryDBModel.entity_id == entity.entity_id,
                                MapEntityMemoryDBModel.entity_type == entity.entity_type,
                            )
                            for entity in deletes
                        ],
                    ),
                ),
            )


async def update_map_entity_interactions(
    updates: Sequence[MapEntityMemoryInteractionUpdate],
) -> None:
    """Persist literal interactions for existing entities, skipping missing records."""
    if not updates:
        return

    async with db_sessionmaker.begin() as session:
        for interaction in updates:
            query = select(MapEntityMemoryDBModel).where(
                MapEntityMemoryDBModel.map_id == interaction.map_id,
                MapEntityMemoryDBModel.entity_id == interaction.entity_id,
                MapEntityMemoryDBModel.entity_type == interaction.entity_type,
            )
            result = await session.execute(query)
            db_obj = result.scalar_one_or_none()
            if db_obj is None:
                logger.warning(
                    "Skipped interaction for missing map entity memory: map_id={}, "
                    "entity_type={}, entity_id={}.",
                    interaction.map_id.name,
                    interaction.entity_type.name,
                    interaction.entity_id,
                )
                continue
            db_obj.last_interaction = interaction.last_interaction
            db_obj.last_interaction_iteration = interaction.last_interaction_iteration
