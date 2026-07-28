"""Tests for streaming view schemas."""

import pytest

from memory.rolling_memory import (
    CurrentMemoryBlock,
    MemorySummary,
    RawMemoryBlock,
    RollingMemory,
)
from streaming.schemas import LogEntryView


@pytest.mark.unit
def test_activity_log_contains_only_exact_raw_memory() -> None:
    """Keep summaries out of the live activity log."""
    memory = RollingMemory(
        current_block=CurrentMemoryBlock(iteration=43, content="Current action."),
        summary_frontier=(
            MemorySummary(
                start_iteration=1,
                end_iteration=40,
                level=2,
                content="Older summarized history.",
            ),
        ),
        loaded_raw_blocks=(
            RawMemoryBlock(iteration=41, content="First recent action."),
            RawMemoryBlock(iteration=42, content="Second recent action."),
        ),
    )

    assert LogEntryView.from_memory(memory) == [
        LogEntryView(iteration=41, thought="First recent action."),
        LogEntryView(iteration=42, thought="Second recent action."),
        LogEntryView(iteration=43, thought="Current action."),
    ]
