"""Behavior tests for shared agent context."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import context as context_module
from agent.context import AgentContext
from agent.state import AgentState
from database.long_term_memory.schemas import LongTermMemoryRead
from memory.long_term_memory import LongTermMemory
from memory.rolling_memory import CurrentMemoryBlock, RollingMemory

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.unit
async def test_begin_iteration_prepares_handler_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Reload long-term memory at the top level, not during internal turns."""
    iteration = 6
    memory = LongTermMemoryRead(title="TEAM_PIKACHU", content="Reliable Electric Pokemon.")
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=iteration,
            rolling_memory=RollingMemory(current_block=CurrentMemoryBlock(iteration=iteration)),
            long_term_memory=LongTermMemory(pieces={memory.title: memory}),
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
    assert not context.state.long_term_memory.pieces
