"""Scheduling tests for rolling-memory compaction."""

from unittest.mock import AsyncMock

import pytest

from common.constants import (
    ROLLING_MEMORY_COMPACTION_RANGE_LIMIT,
    ROLLING_MEMORY_LEAF_SIZE,
    ROLLING_MEMORY_RAW_BLOCK_SOFT_LIMIT,
)
from database.rolling_memory.schemas import MemorySummaryCreate, MemorySummaryRead
from memory.rolling_memory import service
from memory.rolling_memory.schemas import MemorySummary, RawMemoryBlock, RollingMemory


def _raw_blocks(count: int, *, start_iteration: int = 1) -> tuple[RawMemoryBlock, ...]:
    """Build chronological raw blocks for scheduling tests."""
    return tuple(
        RawMemoryBlock(iteration=iteration, content=f"Observed outcome {iteration}.")
        for iteration in range(start_iteration, start_iteration + count)
    )


def _summary(
    *,
    start_iteration: int,
    end_iteration: int,
    level: int,
) -> MemorySummary:
    """Build one frontier summary for scheduling tests."""
    return MemorySummary(
        start_iteration=start_iteration,
        end_iteration=end_iteration,
        level=level,
        content="Durable observed history.",
    )


def _as_read_model(summary: MemorySummaryCreate) -> MemorySummaryRead:
    """Return the repository result corresponding to a create request."""
    return MemorySummaryRead.model_validate(summary)


@pytest.fixture
def compaction_boundaries(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, AsyncMock]:
    """Replace external model and persistence boundaries for scheduling tests."""
    get_llm_response = AsyncMock(return_value="Durable observed history.")
    store_memory_summary = AsyncMock(side_effect=_as_read_model)
    monkeypatch.setattr(service.llm_service, "get_llm_response", get_llm_response)
    monkeypatch.setattr(service, "store_memory_summary", store_memory_summary)
    return get_llm_response, store_memory_summary


@pytest.mark.unit
async def test_compaction_prioritizes_raw_work_within_the_range_budget(
    compaction_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    """Reserve the first bounded-batch slot for an eligible raw leaf."""
    get_llm_response, store_memory_summary = compaction_boundaries
    raw_count = ROLLING_MEMORY_RAW_BLOCK_SOFT_LIMIT + ROLLING_MEMORY_LEAF_SIZE
    memory = RollingMemory(
        loaded_raw_blocks=_raw_blocks(raw_count, start_iteration=121),
        summary_frontier=tuple(
            _summary(
                start_iteration=start_iteration,
                end_iteration=start_iteration + ROLLING_MEMORY_LEAF_SIZE - 1,
                level=1,
            )
            for start_iteration in range(1, 121, ROLLING_MEMORY_LEAF_SIZE)
        ),
    )

    summaries = await service.compact_memory(memory)

    assert summaries == [
        MemorySummaryRead(
            start_iteration=121,
            end_iteration=120 + ROLLING_MEMORY_LEAF_SIZE,
            level=1,
            content="Durable observed history.",
        ),
        MemorySummaryRead(
            start_iteration=1,
            end_iteration=40,
            level=2,
            content="Durable observed history.",
        ),
        MemorySummaryRead(
            start_iteration=41,
            end_iteration=80,
            level=2,
            content="Durable observed history.",
        ),
    ]
    assert get_llm_response.await_count == ROLLING_MEMORY_COMPACTION_RANGE_LIMIT
    assert store_memory_summary.await_count == ROLLING_MEMORY_COMPACTION_RANGE_LIMIT


@pytest.mark.unit
async def test_compaction_advances_up_to_three_parents_below_the_raw_tail_limit(
    compaction_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    """Use the bounded batch for parent work when no raw leaf is due."""
    get_llm_response, store_memory_summary = compaction_boundaries
    memory = RollingMemory(
        loaded_raw_blocks=_raw_blocks(
            ROLLING_MEMORY_RAW_BLOCK_SOFT_LIMIT,
            start_iteration=161,
        ),
        summary_frontier=tuple(
            _summary(
                start_iteration=start_iteration,
                end_iteration=start_iteration + ROLLING_MEMORY_LEAF_SIZE - 1,
                level=1,
            )
            for start_iteration in range(1, 161, ROLLING_MEMORY_LEAF_SIZE)
        ),
    )

    summaries = await service.compact_memory(memory)

    assert summaries == [
        MemorySummaryRead(
            start_iteration=1,
            end_iteration=40,
            level=2,
            content="Durable observed history.",
        ),
        MemorySummaryRead(
            start_iteration=41,
            end_iteration=80,
            level=2,
            content="Durable observed history.",
        ),
        MemorySummaryRead(
            start_iteration=81,
            end_iteration=120,
            level=2,
            content="Durable observed history.",
        ),
    ]
    assert get_llm_response.await_count == ROLLING_MEMORY_COMPACTION_RANGE_LIMIT
    assert store_memory_summary.await_count == ROLLING_MEMORY_COMPACTION_RANGE_LIMIT


@pytest.mark.unit
async def test_compaction_does_nothing_without_an_eligible_range(
    compaction_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    """Avoid model and persistence calls when maintenance has no work."""
    get_llm_response, store_memory_summary = compaction_boundaries
    memory = RollingMemory(
        loaded_raw_blocks=_raw_blocks(
            ROLLING_MEMORY_RAW_BLOCK_SOFT_LIMIT,
            start_iteration=21,
        ),
        summary_frontier=(_summary(start_iteration=1, end_iteration=20, level=1),),
    )

    summaries = await service.compact_memory(memory)

    assert summaries == []
    get_llm_response.assert_not_awaited()
    store_memory_summary.assert_not_awaited()
