"""Behavior tests for overworld long-term-memory tools."""

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.state import AgentState
from agent.subflows.overworld_handler.context import OverworldContext
from agent.subflows.overworld_handler.tools.create_long_term_memory import (
    interface as create_interface,
)
from agent.subflows.overworld_handler.tools.create_long_term_memory import (
    service as create_service,
)
from agent.subflows.overworld_handler.tools.update_long_term_memory import (
    interface as update_interface,
)
from agent.subflows.overworld_handler.tools.update_long_term_memory import (
    service as update_service,
)
from agent.subflows.overworld_handler.tools.update_long_term_memory.schemas import (
    UpdateType,
)
from database.long_term_memory.schemas import LongTermMemoryCreate, LongTermMemoryUpdate

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from agent.subflows.overworld_handler.utils import OverworldToolResult


@pytest.mark.unit
async def test_created_memory_can_be_updated_in_the_same_overworld_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Expose each successful write immediately to later fixed-tool calls."""
    create_record = AsyncMock()
    update_record = AsyncMock()
    monkeypatch.setattr(create_service, "create_long_term_memory_record", create_record)
    monkeypatch.setattr(update_service, "update_long_term_memory_record", update_record)
    monkeypatch.setattr(
        "streaming.server.update_background_log_from_memory",
        MagicMock(),
    )
    complete_action = AsyncMock(side_effect=lambda _context, result: ["screenshot", result])
    monkeypatch.setattr(create_interface, "complete_overworld_action", complete_action)
    monkeypatch.setattr(update_interface, "complete_overworld_action", complete_action)

    context = OverworldContext(
        state=AgentState(folder=tmp_path, iteration=31),
        emulator=MagicMock(),
        current_map=MagicMock(),
        available_long_term_memory_titles=("MAP_PALLET_TOWN",),
    )
    create_tool = create_interface.build_create_long_term_memory_tool(context)
    update_tool = update_interface.build_update_long_term_memory_tool(context)
    create_memory = cast(
        "Callable[[str, str], Awaitable[OverworldToolResult]]",
        create_tool.function,
    )
    update_memory = cast(
        "Callable[[str, UpdateType, str], Awaitable[OverworldToolResult]]",
        update_tool.function,
    )

    create_result = await create_memory(
        "team pikachu",
        "Pikachu is a fast and reliable lead.",
    )
    update_result = await update_memory(
        "TEAM_PIKACHU",
        UpdateType.APPEND,
        "Electric attacks are its specialty.",
    )

    assert context.available_long_term_memory_titles == (
        "MAP_PALLET_TOWN",
        "TEAM_PIKACHU",
    )
    assert context.state.long_term_memory.pieces["TEAM_PIKACHU"].content == (
        "Pikachu is a fast and reliable lead.\nElectric attacks are its specialty."
    )
    assert cast("str", create_result[-1]) in context.state.rolling_memory.current_block.content
    assert cast("str", update_result[-1]) in context.state.rolling_memory.current_block.content
    create_record.assert_awaited_once_with(
        LongTermMemoryCreate(
            title="TEAM_PIKACHU",
            content="Pikachu is a fast and reliable lead.",
            iteration=31,
        ),
    )
    update_record.assert_awaited_once_with(
        LongTermMemoryUpdate(
            title="TEAM_PIKACHU",
            content=("Pikachu is a fast and reliable lead.\nElectric attacks are its specialty."),
            iteration=31,
        ),
    )
