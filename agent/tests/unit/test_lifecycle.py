"""Behavior tests for shared agent context."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import context as context_module
from agent.context import AgentContext
from agent.state import AgentState
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
