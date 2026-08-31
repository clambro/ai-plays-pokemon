"""Persistence operations for observed map-boundary memory."""

from typing import TYPE_CHECKING

from sqlalchemy import select

from database.db_config import db_sessionmaker
from database.map_boundary_memory.model import MapBoundaryMemoryDBModel
from database.map_boundary_memory.schemas import (
    MapBoundaryMemoryCreateUpdate,
    MapBoundaryMemoryRead,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from common.enums import MapId


async def get_map_boundary_memories_for_map(map_id: MapId) -> list[MapBoundaryMemoryRead]:
    """Get all known coordinate mappings for observed boundaries on a map."""
    async with db_sessionmaker() as session:
        query = select(MapBoundaryMemoryDBModel).where(MapBoundaryMemoryDBModel.map_id == map_id)
        result = await session.execute(query)
        db_objs = result.scalars().all()

    return [MapBoundaryMemoryRead.model_validate(db_obj) for db_obj in db_objs]


async def remember_map_boundaries(
    boundaries: Sequence[MapBoundaryMemoryCreateUpdate],
) -> None:
    """Create or refresh the known coordinate mapping for a map boundary."""
    if not boundaries:
        return

    async with db_sessionmaker.begin() as session:
        for boundary in boundaries:
            db_obj = await session.get(
                MapBoundaryMemoryDBModel,
                (boundary.map_id, boundary.direction, boundary.row, boundary.col),
            )
            if db_obj is None:
                session.add(MapBoundaryMemoryDBModel(**boundary.model_dump()))
                continue

            db_obj.destination_map_id = boundary.destination_map_id
            db_obj.destination_row = boundary.destination_row
            db_obj.destination_col = boundary.destination_col
