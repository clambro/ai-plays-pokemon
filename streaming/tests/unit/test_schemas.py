"""Tests for streaming view schemas."""

import pytest

from common.constants import CAPTURED_DIALOG_MARKER, SCRIPTED_LOOP_MARKER
from memory.rolling_memory.schemas import (
    CurrentMemoryBlock,
    MemorySummary,
    RawMemoryBlock,
    RollingMemory,
)
from streaming.schemas import LogEntryView


@pytest.mark.unit
def test_activity_log_omits_captured_dialogue() -> None:
    """Hide marked game dialog without hiding other external notices."""
    memory = RollingMemory(
        current_block=CurrentMemoryBlock(
            iteration=43,
            content=f"{SCRIPTED_LOOP_MARKER} Current warning.",
        ),
        summary_frontier=(
            MemorySummary(
                start_iteration=1,
                end_iteration=40,
                level=2,
                content="Older summarized history.",
            ),
        ),
        loaded_raw_blocks=(
            RawMemoryBlock(
                iteration=41,
                content=f'First recent action.\n\n{CAPTURED_DIALOG_MARKER} "Dialog."',
            ),
            RawMemoryBlock(
                iteration=42,
                content=f'{CAPTURED_DIALOG_MARKER} "Dialog only."',
            ),
        ),
    )

    assert LogEntryView.from_memory(memory) == [
        LogEntryView(iteration=41, thought="First recent action."),
        LogEntryView(iteration=43, thought=f"{SCRIPTED_LOOP_MARKER} Current warning."),
    ]
