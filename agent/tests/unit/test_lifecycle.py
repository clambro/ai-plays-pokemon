"""Behavior tests for shared agent context."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import context as context_module
from agent.context import AgentContext
from agent.state import AgentState
from database.rolling_memory.schemas import RawMemoryBlockRead
from memory.rolling_memory import service as rolling_memory_service
from memory.rolling_memory.schemas import CurrentMemoryBlock, RollingMemory

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.unit
async def test_begin_iteration_prepares_handler_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Initialize rolling memory once at the start of a handler activation."""
    iteration = 6
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=iteration,
            rolling_memory=RollingMemory(current_block=CurrentMemoryBlock(iteration=iteration)),
        ),
        emulator=MagicMock(),
    )
    prepared_memory = RollingMemory(
        current_block=CurrentMemoryBlock(iteration=iteration),
    )
    original_block = context.state.rolling_memory.current_block
    initialize_memory = AsyncMock(return_value=prepared_memory)
    monkeypatch.setattr(context_module, "initialize_memory", initialize_memory)

    await context.begin_iteration()

    initialize_memory.assert_awaited_once_with(original_block)
    assert context.state.iteration == iteration


@pytest.mark.unit
async def test_complete_iteration_advances_after_maintenance_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Keep live memory aligned after persistence succeeds but maintenance fails."""
    iteration = 6
    content = "I tried to move north, but a wall blocked the way."
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=iteration,
            rolling_memory=RollingMemory(
                current_block=CurrentMemoryBlock(iteration=iteration, content=content),
            ),
        ),
        emulator=MagicMock(),
    )
    monkeypatch.setattr(
        rolling_memory_service,
        "finalize_raw_memory_block",
        AsyncMock(return_value=RawMemoryBlockRead(iteration=iteration, content=content)),
    )
    monkeypatch.setattr(
        rolling_memory_service,
        "compact_memory",
        AsyncMock(side_effect=RuntimeError("compaction unavailable")),
    )

    await context.complete_iteration()

    assert context.state.iteration == iteration + 1
    assert context.state.rolling_memory.current_block == CurrentMemoryBlock(
        iteration=iteration + 1,
    )
    assert context.state.rolling_memory.loaded_raw_blocks[-1].iteration == iteration
    assert context.state.rolling_memory.loaded_raw_blocks[-1].content == content
