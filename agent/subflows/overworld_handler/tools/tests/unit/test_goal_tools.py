"""Behavior tests for overworld goal lifecycle tools."""

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.state import AgentState
from agent.subflows.overworld_handler.context import OverworldContext
from agent.subflows.overworld_handler.tools.create_goal import interface as create_interface
from agent.subflows.overworld_handler.tools.delete_goal import interface as delete_interface
from agent.subflows.overworld_handler.tools.update_goal import interface as update_interface
from memory.goals import Goal, GoalPriority, Goals

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from agent.subflows.overworld_handler.utils import OverworldToolResult


@pytest.mark.unit
async def test_goal_tools_create_update_and_delete_one_goal_at_a_time(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Make each lifecycle change immediately visible to later tool calls."""
    primary = Goal(goal="Defeat Brock.", priority=GoalPriority.PRIMARY)
    context = OverworldContext(
        state=AgentState(folder=tmp_path, goals=Goals(goals=[primary])),
        emulator=MagicMock(),
        current_map=MagicMock(),
        available_long_term_memory_titles=(),
    )
    complete_action = AsyncMock(side_effect=lambda _context, result: ["screenshot", result])
    monkeypatch.setattr(create_interface, "complete_overworld_action", complete_action)
    monkeypatch.setattr(update_interface, "complete_overworld_action", complete_action)
    monkeypatch.setattr(delete_interface, "complete_overworld_action", complete_action)
    create = cast(
        "Callable[[str, GoalPriority], Awaitable[OverworldToolResult]]",
        create_interface.build_create_goal_tool(context).function,
    )
    update = cast(
        "Callable[[int, str, GoalPriority], Awaitable[OverworldToolResult]]",
        update_interface.build_update_goal_tool(context).function,
    )
    delete = cast(
        "Callable[[int], Awaitable[OverworldToolResult]]",
        delete_interface.build_delete_goal_tool(context).function,
    )

    created = Goal(goal="Reach Cerulean City.", priority=GoalPriority.SECONDARY)
    create_result = await create(created.goal, created.priority)
    assert context.state.goals.goals == [primary, created]

    revised = Goal(
        goal="Reach Cerulean City through Mt. Moon.",
        priority=GoalPriority.SECONDARY,
    )
    update_result = await update(
        1,
        revised.goal,
        revised.priority,
    )
    assert context.state.goals.goals == [primary, revised]

    delete_result = await delete(1)
    assert context.state.goals.goals == [primary]

    assert "Created goal" in cast("str", create_result[-1])
    assert "Updated goal" in cast("str", update_result[-1])
    assert "Deleted goal" in cast("str", delete_result[-1])
    assert not context.state.rolling_memory.current_block.content
