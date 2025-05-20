from sqlalchemy import select, update

from database.db_config import db_sessionmaker
from database.warp_memory.model import WarpMemoryDBModel
from database.warp_memory.schemas import WarpMemoryCreate, WarpMemoryRead, WarpMemoryUpdate


async def create_warp_memory(warp: WarpMemoryCreate) -> WarpMemoryRead:
    """Create a new warp memory."""
    async with db_sessionmaker() as session:
        db_obj = WarpMemoryDBModel(
            map_id=warp.map_id,
            warp_id=warp.warp_id,
            description=None,
            create_iteration=warp.iteration,
            update_iteration=warp.iteration,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return WarpMemoryRead.model_validate(db_obj)


async def get_warp_memories_for_map(map_id: int) -> list[WarpMemoryRead]:
    """Get all warp memories for a map."""
    async with db_sessionmaker() as session:
        query = select(WarpMemoryDBModel).where(WarpMemoryDBModel.map_id == map_id)
        result = await session.execute(query)
        db_objs = result.scalars().all()

    return [WarpMemoryRead.model_validate(d) for d in db_objs]


async def update_warp_memory(warp: WarpMemoryUpdate) -> WarpMemoryRead:
    """Update the description of a warp memory."""
    async with db_sessionmaker() as session:
        query = (
            update(WarpMemoryDBModel)
            .where(
                WarpMemoryDBModel.map_id == warp.map_id.value,
                WarpMemoryDBModel.warp_id == warp.warp_id,
            )
            .values(
                description=warp.description,
                update_iteration=warp.iteration,
            )
            .returning(WarpMemoryDBModel)
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(
                f"No warp memory found for map_id: {warp.map_id} and warp_id: {warp.warp_id}",
            )

        await session.commit()

        return WarpMemoryRead.model_validate(db_obj)
