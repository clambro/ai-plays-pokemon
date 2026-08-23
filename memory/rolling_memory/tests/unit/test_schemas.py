"""Tests for rolling-memory schema behavior."""

import pytest

from memory.rolling_memory.schemas import (
    CurrentMemoryBlock,
    RollingMemory,
)


@pytest.mark.unit
def test_current_iteration_accumulates_one_chronological_memory_block() -> None:
    """Keep every write from one iteration together and in order."""
    iteration = 42
    memory = RollingMemory(current_block=CurrentMemoryBlock(iteration=iteration))

    memory.add_memory("Selected the navigation tool.")
    memory.add_memory("Reached the Pokémon Center.")

    assert len(memory.raw_blocks) == 1
    assert memory.current_block.iteration == iteration
    assert memory.current_block.content == (
        "Selected the navigation tool.\n\nReached the Pokémon Center."
    )
