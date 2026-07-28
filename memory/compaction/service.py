"""Business logic for hierarchical rolling-memory compaction."""

import asyncio
from typing import TYPE_CHECKING

from common.constants import (
    ROLLING_MEMORY_LEAF_SIZE,
    ROLLING_MEMORY_SUMMARY_MAX_CHARACTERS,
)
from database.rolling_memory.repository import store_memory_summary
from database.rolling_memory.schemas import (
    MemorySummaryCreate,
    MemorySummaryRead,
)
from llm.service import OpenAILLMService
from memory.compaction.prompts import COMPACTION_PROMPT, SYSTEM_PROMPT

if TYPE_CHECKING:
    from memory.rolling_memory import (
        MemorySummary,
        RollingMemory,
    )

llm_service = OpenAILLMService()


async def compact_memory(memory: RollingMemory) -> list[MemorySummaryRead]:
    """Compact every range eligible in the current rolling-memory view."""
    requests = []
    if len(memory.loaded_raw_blocks) > ROLLING_MEMORY_LEAF_SIZE:
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
    summary = await llm_service.get_llm_response(
        prompt,
        system_prompt=SYSTEM_PROMPT,
    )
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
