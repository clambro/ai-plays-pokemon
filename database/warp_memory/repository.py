"""Persistence operations for warp memory."""

from typing import TYPE_CHECKING

from sqlalchemy import select

from database.db_config import db_sessionmaker
from database.warp_memory.model import WarpMemoryDBModel
from database.warp_memory.schemas import WarpMemoryCreateUpdate, WarpMemoryRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from common.enums import MapId


async def get_warp_memories_for_map(map_id: MapId) -> list[WarpMemoryRead]:
    """Get all discovered warps for a map."""
    async with db_sessionmaker() as session:
        query = select(WarpMemoryDBModel).where(WarpMemoryDBModel.map_id == map_id)
        result = await session.execute(query)
        db_objs = result.scalars().all()

    return [WarpMemoryRead.model_validate(db_obj) for db_obj in db_objs]


async def remember_warps(warps: list[WarpMemoryCreateUpdate]) -> None:
    """Create or refresh discovered warps from current game state."""
    if not warps:
        return

    async with db_sessionmaker.begin() as session:
        for warp in warps:
            await _upsert_warp(session, warp)


async def record_warp_usage(
    *,
    iteration: int,
    source_map_id: MapId,
    source_warp_id: int,
    destination: WarpMemoryCreateUpdate,
) -> bool:
    """Timestamp a known source warp and persist the observed destination warp."""
    async with db_sessionmaker.begin() as session:
        destination_db_obj = await _upsert_warp(session, destination)
        source = (
            destination_db_obj
            if (source_map_id, source_warp_id) == (destination.map_id, destination.warp_id)
            else await session.get(WarpMemoryDBModel, (source_map_id, source_warp_id))
        )
        destination_db_obj.last_used_iteration = iteration
        if source is None:
            return False
        source.last_used_iteration = iteration
        return True


async def _upsert_warp(
    session: AsyncSession,
    warp: WarpMemoryCreateUpdate,
) -> WarpMemoryDBModel:
    """Create or refresh one warp inside the caller's transaction."""
    db_obj = await session.get(WarpMemoryDBModel, (warp.map_id, warp.warp_id))
    if db_obj is None:
        db_obj = WarpMemoryDBModel(
            map_id=warp.map_id,
            warp_id=warp.warp_id,
            row=warp.row,
            col=warp.col,
            destination_map_id=warp.destination_map_id,
            destination_warp_id=warp.destination_warp_id,
            activation=warp.activation,
        )
        session.add(db_obj)
    else:
        db_obj.row = warp.row
        db_obj.col = warp.col
        db_obj.destination_map_id = warp.destination_map_id
        db_obj.destination_warp_id = warp.destination_warp_id
        db_obj.activation = warp.activation
    return db_obj
