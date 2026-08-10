"""Behavior tests for the long-term-memory retrieval tool."""

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.context import AgentContext
from agent.overworld.tools.retrieve_long_term_memory import (
    interface,
    service,
)
from agent.state import AgentState
from database.long_term_memory.schemas import LongTermMemoryRead
from memory.long_term_memory import LongTermMemory

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from agent.overworld.utils import OverworldToolResult


@pytest.mark.unit
async def test_retrieve_tool_appends_live_memory_and_returns_the_new_document(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Make retrieved documents immediately visible to the active conversation."""
    previous = LongTermMemoryRead(title="MAP_PALLET_TOWN", content="Starting town.")
    retrieved = LongTermMemoryRead(title="TEAM_PIKACHU", content="Reliable Electric Pokemon.")
    get_memories = AsyncMock(return_value=[retrieved])
    monkeypatch.setattr(service, "get_long_term_memories", get_memories)
    complete_action = AsyncMock(side_effect=lambda _context, result: ["screenshot", result])
    monkeypatch.setattr(interface, "complete_overworld_action", complete_action)
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=41,
            long_term_memory=LongTermMemory(pieces={previous.title: previous}),
        ),
        emulator=MagicMock(),
    )
    available_titles = [previous.title, retrieved.title]
    tool = interface.build_retrieve_long_term_memory_tool(context, available_titles)
    retrieve = cast(
        "Callable[[str], Awaitable[OverworldToolResult]]",
        tool.function,
    )

    output = await retrieve(retrieved.title)

    assert context.state.long_term_memory.pieces == {
        previous.title: previous,
        retrieved.title: retrieved,
    }
    result = cast("str", output[-1])
    assert retrieved.content in result
    assert not context.state.rolling_memory.current_block.content
