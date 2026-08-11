"""Persistence and compaction workflow for rolling memory."""

import asyncio

from common.constants import (
    ROLLING_MEMORY_LEAF_SIZE,
    ROLLING_MEMORY_SUMMARY_MAX_CHARACTERS,
)
from database.rolling_memory.repository import (
    finalize_raw_memory_block,
    get_memory_summary_frontier,
    get_raw_memory_blocks_after,
    store_memory_summary,
)
from database.rolling_memory.schemas import (
    MemorySummaryCreate,
    MemorySummaryRead,
    RawMemoryBlockCreate,
)
from llm.service import OpenAILLMService
from memory.rolling_memory.prompts import COMPACTION_PROMPT, SYSTEM_PROMPT
from memory.rolling_memory.schemas import (
    CurrentMemoryBlock,
    MemorySummary,
    RawMemoryBlock,
    RollingMemory,
)

llm_service = OpenAILLMService()


async def initialize_memory(current_block: CurrentMemoryBlock) -> RollingMemory:
    """Initialize a loop's working memory from SQLite and its current block."""
    summary_records = await get_memory_summary_frontier()
    summary_frontier = tuple(
        MemorySummary(
            start_iteration=record.start_iteration,
            end_iteration=record.end_iteration,
            level=record.level,
            content=record.content,
        )
        for record in summary_records
    )
    covered_iteration = summary_frontier[-1].end_iteration if summary_frontier else -1
    raw_records = await get_raw_memory_blocks_after(covered_iteration)
    loaded_raw_blocks = tuple(
        RawMemoryBlock(
            iteration=record.iteration,
            content=record.content,
        )
        for record in raw_records
    )

    latest_finalized_iteration = (
        loaded_raw_blocks[-1].iteration if loaded_raw_blocks else covered_iteration
    )
    if current_block.iteration <= latest_finalized_iteration:
        current_block = CurrentMemoryBlock(
            iteration=latest_finalized_iteration + 1,
        )

    return RollingMemory(
        current_block=current_block,
        summary_frontier=summary_frontier,
        loaded_raw_blocks=loaded_raw_blocks,
    )


async def finalize_iteration(memory: RollingMemory) -> None:
    """Persist and compact the completed iteration."""
    record = await finalize_raw_memory_block(
        RawMemoryBlockCreate(
            iteration=memory.current_block.iteration,
            content=memory.current_block.content,
        ),
    )
    finalized_block = RawMemoryBlock(
        iteration=record.iteration,
        content=record.content,
    )
    await compact_memory(
        RollingMemory(
            current_block=memory.current_block,
            summary_frontier=memory.summary_frontier,
            loaded_raw_blocks=(*memory.loaded_raw_blocks, finalized_block),
        ),
    )


async def compact_memory(memory: RollingMemory) -> list[MemorySummaryRead]:
    """Compact every range eligible in the current rolling-memory view."""
    requests = []
    if len(memory.loaded_raw_blocks) >= ROLLING_MEMORY_LEAF_SIZE * 2:
        raw_blocks = memory.loaded_raw_blocks[:ROLLING_MEMORY_LEAF_SIZE]
        requests.append(
            _summarize(
                start_iteration=raw_blocks[0].iteration,
                end_iteration=raw_blocks[-1].iteration,
                level=1,
                source="\n\n".join(map(str, raw_blocks)),
            ),
        )

    requests.extend(
        _summarize(
            start_iteration=left.start_iteration,
            end_iteration=right.end_iteration,
            level=left.level + 1,
            source=f"{left}\n\n{right}",
        )
        for left, right in _find_parent_pairs(memory.summary_frontier)
    )
    if not requests:
        return []

    return list(await asyncio.gather(*requests))


async def _summarize(
    *,
    start_iteration: int,
    end_iteration: int,
    level: int,
    source: str,
) -> MemorySummaryRead:
    """Summarize and store one selected memory range."""
    prompt = COMPACTION_PROMPT.format(
        start_iteration=start_iteration,
        end_iteration=end_iteration,
        max_characters=ROLLING_MEMORY_SUMMARY_MAX_CHARACTERS,
        source=source,
    )
    summary = await llm_service.get_llm_response(prompt, system_prompt=SYSTEM_PROMPT)
    return await store_memory_summary(
        MemorySummaryCreate(
            start_iteration=start_iteration,
            end_iteration=end_iteration,
            level=level,
            content=summary,
        ),
    )


def _find_parent_pairs(
    frontier: tuple[MemorySummary, ...],
) -> list[tuple[MemorySummary, MemorySummary]]:
    """Find every non-overlapping adjacent pair at the same tree level."""
    summaries_by_level: dict[int, list[MemorySummary]] = {}
    for summary in frontier:
        summaries_by_level.setdefault(summary.level, []).append(summary)

    pairs = []
    for summaries in summaries_by_level.values():
        summaries_iter = iter(summaries)
        for left in summaries_iter:
            right = next(summaries_iter, None)
            if right is not None and left.end_iteration + 1 == right.start_iteration:
                pairs.append((left, right))
    return pairs
