from sqlalchemy import select, update

from database.db_config import db_sessionmaker
from database.sign_memory.model import SignMemoryDBModel
from database.sign_memory.schemas import SignMemoryCreate, SignMemoryRead, SignMemoryUpdate


async def create_sign_memory(sign: SignMemoryCreate) -> SignMemoryRead:
    """Create a new sign memory."""
    async with db_sessionmaker() as session:
        db_obj = SignMemoryDBModel(
            map_id=sign.map_id,
            sign_id=sign.sign_id,
            description=None,
            create_iteration=sign.iteration,
            update_iteration=sign.iteration,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return SignMemoryRead.model_validate(db_obj)


async def get_sign_memories_for_map(map_id: int) -> list[SignMemoryRead]:
    """Get all sign memories for a map."""
    async with db_sessionmaker() as session:
        query = select(SignMemoryDBModel).where(SignMemoryDBModel.map_id == map_id)
        result = await session.execute(query)
        db_objs = result.scalars().all()

    return [SignMemoryRead.model_validate(d) for d in db_objs]


async def update_sign_memory(sign: SignMemoryUpdate) -> SignMemoryRead:
    """Update the description of a sign memory."""
    async with db_sessionmaker() as session:
        query = (
            update(SignMemoryDBModel)
            .where(
                SignMemoryDBModel.map_id == sign.map_id.value,
                SignMemoryDBModel.sign_id == sign.sign_id,
            )
            .values(
                description=sign.description,
                update_iteration=sign.iteration,
            )
            .returning(SignMemoryDBModel)
        )
        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise ValueError(
                f"No sign memory found for map_id {sign.map_id} and sign_id {sign.sign_id}",
            )

        await session.commit()

    return SignMemoryRead.model_validate(db_obj)
