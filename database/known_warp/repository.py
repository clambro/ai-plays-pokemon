from sqlalchemy import select, update

from database.db_config import db_sessionmaker
from database.known_warp.model import KnownWarpTable
from database.known_warp.schemas import KnownWarpCreate, KnownWarpRead


async def create_known_warp(warp: KnownWarpCreate) -> KnownWarpRead:
    """Create a new known warp."""
    async with db_sessionmaker() as session:
        db_obj = KnownWarpTable(
            map_id=warp.map_id,
            warp_id=warp.warp_id,
            y=warp.y,
            x=warp.x,
            destination=warp.destination,
            description=warp.description,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return KnownWarpRead.model_validate(db_obj)


async def get_known_warp(map_id: int, warp_id: int) -> KnownWarpRead:
    """Get a known warp by map id and warp id."""
    async with db_sessionmaker() as session:
        query = select(KnownWarpTable).where(
            KnownWarpTable.map_id == map_id,
            KnownWarpTable.warp_id == warp_id,
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(f"No known warp found for map_id: {map_id} and warp_id: {warp_id}")

    return KnownWarpRead.model_validate(db_obj)


async def update_known_warp_description(
    map_id: int,
    warp_id: int,
    description: str,
) -> KnownWarpRead:
    """Update the description of a known warp."""
    async with db_sessionmaker() as session:
        query = (
            update(KnownWarpTable)
            .where(
                KnownWarpTable.map_id == map_id,
                KnownWarpTable.warp_id == warp_id,
            )
            .values(description=description)
            .returning(KnownWarpTable)
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(f"No known warp found for map_id: {map_id} and warp_id: {warp_id}")

        await session.commit()

        return KnownWarpRead.model_validate(db_obj)
