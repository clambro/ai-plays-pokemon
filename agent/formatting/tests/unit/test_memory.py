"""Tests for model-facing rolling-memory formatting."""

import pytest

from agent.formatting.memory import format_rolling_memory
from memory.rolling_memory.schemas import (
    CurrentMemoryBlock,
    MemorySummary,
    RawMemoryBlock,
    RollingMemory,
)


@pytest.mark.unit
def test_prompt_memory_is_chronological_across_summary_and_raw_history() -> None:
    """Render older summaries before exact recent and current memories."""
    memory = RollingMemory(
        current_block=CurrentMemoryBlock(iteration=43, content="Entered the mart."),
        summary_frontier=(
            MemorySummary(
                start_iteration=1,
                end_iteration=40,
                level=2,
                content="Reached Cerulean City.",
            ),
        ),
        loaded_raw_blocks=(
            RawMemoryBlock(iteration=41, content="Walked toward the mart."),
            RawMemoryBlock(iteration=42, content="Opened the mart door."),
        ),
    )

    prompt_memory = format_rolling_memory(memory)

    assert prompt_memory.index("[1-40]:") < prompt_memory.index("[41]:")
    assert prompt_memory.index("[41]:") < prompt_memory.index("[42]:")
    assert prompt_memory.index("[42]:") < prompt_memory.index("[43]:")
