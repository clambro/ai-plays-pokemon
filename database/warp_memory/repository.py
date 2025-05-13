from sqlalchemy import select, update

from database.db_config import db_sessionmaker
from database.warp_memory.model import WarpMemoryTable
from database.warp_memory.schemas import WarpMemoryCreate, WarpMemoryRead


async def create_warp_memory(warp: WarpMemoryCreate) -> WarpMemoryRead:
    """Create a new warp memory."""
    async with db_sessionmaker() as session:
        db_obj = WarpMemoryTable(
            map_id=warp.map_id,
            warp_id=warp.warp_id,
            description=warp.description,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return WarpMemoryRead.model_validate(db_obj)


async def get_warp_memory(map_id: int, warp_id: int) -> WarpMemoryRead:
    """Get a warp memory by map id and warp id."""
    async with db_sessionmaker() as session:
        query = select(WarpMemoryTable).where(
            WarpMemoryTable.map_id == map_id,
            WarpMemoryTable.warp_id == warp_id,
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(f"No warp memory found for map_id: {map_id} and warp_id: {warp_id}")

    return WarpMemoryRead.model_validate(db_obj)


async def update_known_warp_description(
    map_id: int,
    warp_id: int,
    description: str,
) -> WarpMemoryRead:
    """Update the description of a warp memory."""
    async with db_sessionmaker() as session:
        query = (
            update(WarpMemoryTable)
            .where(
                WarpMemoryTable.map_id == map_id,
                WarpMemoryTable.warp_id == warp_id,
            )
            .values(description=description)
            .returning(WarpMemoryTable)
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(f"No known warp found for map_id: {map_id} and warp_id: {warp_id}")

        await session.commit()

        return WarpMemoryRead.model_validate(db_obj)
