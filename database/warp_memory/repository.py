"""Persistence operations for warp memory."""

from typing import TYPE_CHECKING

from sqlalchemy import select

from common.enums import MapId
from database.db_config import db_sessionmaker
from database.warp_memory.model import WarpMemoryDBModel
from database.warp_memory.schemas import WarpMemoryCreateUpdate, WarpMemoryRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_warp_memories_for_map(map_id: MapId) -> list[WarpMemoryRead]:
    """Get all observed routes from a map, including alternative destinations of each warp."""
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
    """Mark the travelled route and the observed arrival-side route as used."""
    async with db_sessionmaker.begin() as session:
        arrival = await _upsert_warp(session, destination)
        if destination.destination_map_id == MapId.UNKNOWN:
            arrival = (
                await session.get(
                    WarpMemoryDBModel,
                    (destination.map_id, destination.warp_id, source_map_id, source_warp_id),
                )
                or arrival
            )
        if arrival is not None:
            arrival.last_used_iteration = iteration
        source = await session.scalar(
            select(WarpMemoryDBModel)
            .where(
                WarpMemoryDBModel.map_id == source_map_id,
                WarpMemoryDBModel.warp_id == source_warp_id,
            )
            .limit(1)
        )
        if source is None:
            return False
        route = await _upsert_warp(
            session,
            WarpMemoryCreateUpdate(
                map_id=source_map_id,
                warp_id=source_warp_id,
                row=source.row,
                col=source.col,
                destination_map_id=destination.map_id,
                destination_warp_id=destination.warp_id,
                activation=source.activation,
            ),
        )
        if route is not None:
            route.last_used_iteration = iteration
        return True


async def _upsert_warp(
    session: AsyncSession,
    warp: WarpMemoryCreateUpdate,
) -> WarpMemoryDBModel | None:
    """Retain real destinations and resolve UNKNOWN in place; ignore unresolved reobservations."""
    records = (
        await session.scalars(
            select(WarpMemoryDBModel).where(
                WarpMemoryDBModel.map_id == warp.map_id,
                WarpMemoryDBModel.warp_id == warp.warp_id,
            )
        )
    ).all()
    if warp.destination_map_id == MapId.UNKNOWN and records:
        return next(
            (record for record in records if record.destination_map_id == MapId.UNKNOWN),
            None,
        )
    db_obj = next(
        (
            record
            for record in records
            if record.destination_map_id == MapId.UNKNOWN
            or (record.destination_map_id, record.destination_warp_id)
            == (warp.destination_map_id, warp.destination_warp_id)
        ),
        None,
    )
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
