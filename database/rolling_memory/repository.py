"""Persistence operations for rolling memory."""

from sqlalchemy import select
from sqlalchemy.orm import aliased

from database.db_config import db_sessionmaker
from database.rolling_memory.model import MemorySummaryDBModel, RawMemoryBlockDBModel
from database.rolling_memory.schemas import (
    MemorySummaryCreate,
    MemorySummaryRead,
    RawMemoryBlockCreate,
    RawMemoryBlockRead,
)


async def finalize_raw_memory_block(block: RawMemoryBlockCreate) -> RawMemoryBlockRead:
    """Persist one finalized application iteration."""
    async with db_sessionmaker() as session:
        db_obj = RawMemoryBlockDBModel(
            iteration=block.iteration,
            content=block.content,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return RawMemoryBlockRead.model_validate(db_obj)


async def get_recent_raw_memory_blocks(limit: int) -> list[RawMemoryBlockRead]:
    """Load the most recent raw blocks in chronological order.

    Args:
        limit: Maximum number of blocks to load.

    Returns:
        Up to ``limit`` blocks ordered from oldest to newest.
    """
    async with db_sessionmaker() as session:
        query = (
            select(RawMemoryBlockDBModel)
            .order_by(RawMemoryBlockDBModel.iteration.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        db_objs = list(reversed(result.scalars().all()))

    return [RawMemoryBlockRead.model_validate(db_obj) for db_obj in db_objs]


async def get_raw_memory_blocks(
    *,
    start_iteration: int,
    end_iteration: int,
) -> list[RawMemoryBlockRead]:
    """Load raw blocks from an inclusive iteration range.

    Args:
        start_iteration: First iteration to include.
        end_iteration: Last iteration to include.

    Returns:
        Matching blocks in chronological order.
    """
    async with db_sessionmaker() as session:
        query = (
            select(RawMemoryBlockDBModel)
            .where(
                RawMemoryBlockDBModel.iteration >= start_iteration,
                RawMemoryBlockDBModel.iteration <= end_iteration,
            )
            .order_by(RawMemoryBlockDBModel.iteration)
        )
        result = await session.execute(query)
        db_objs = result.scalars().all()

    return [RawMemoryBlockRead.model_validate(db_obj) for db_obj in db_objs]


async def store_memory_summary(summary: MemorySummaryCreate) -> MemorySummaryRead:
    """Persist one derived summary."""
    async with db_sessionmaker() as session:
        db_obj = MemorySummaryDBModel(
            start_iteration=summary.start_iteration,
            end_iteration=summary.end_iteration,
            level=summary.level,
            content=summary.content,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

    return MemorySummaryRead.model_validate(db_obj)


async def get_memory_summary_frontier() -> list[MemorySummaryRead]:
    """Load the highest available non-overlapping memory summaries."""
    summary = aliased(MemorySummaryDBModel)
    covering_summary = aliased(MemorySummaryDBModel)
    has_covering_summary = (
        select(covering_summary.start_iteration)
        .where(
            covering_summary.level > summary.level,
            covering_summary.start_iteration <= summary.start_iteration,
            covering_summary.end_iteration >= summary.end_iteration,
        )
        .exists()
    )

    async with db_sessionmaker() as session:
        query = select(summary).where(~has_covering_summary).order_by(summary.start_iteration)
        result = await session.execute(query)
        db_objs = result.scalars().all()

    return [MemorySummaryRead.model_validate(db_obj) for db_obj in db_objs]
