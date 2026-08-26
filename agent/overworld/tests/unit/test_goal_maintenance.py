"""Overworld behavior test for forced periodic goal updates."""

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.context import AgentContext
from agent.overworld.tools import registry
from agent.overworld.tools.set_goal import interface as goal_interface
from agent.state import AgentState
from memory.goals import Goal, Goals

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from pydantic_ai import FunctionToolset

type _GoalToolFunction = Callable[..., Awaitable[object]]


def _toolset(context: AgentContext) -> FunctionToolset[AgentContext]:
    game_state = MagicMock()
    game_state.player.is_biking = False
    game_state.player.has_pokedex = False
    game_state.can_use_strength = False
    return registry.build_overworld_toolset(
        context,
        current_map=MagicMock(),
        map_view=MagicMock(),
        game_state=game_state,
    )


@pytest.mark.unit
async def test_stale_goal_forces_one_update_then_restores_normal_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Require one successful goal call after 300 iterations, then exit maintenance."""
    review_iteration = 300
    goal_text = "I will reach the next town."
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=review_iteration,
            goals=Goals(goals=[Goal(goal=goal_text, updated_at_iteration=0)]),
        ),
        emulator=MagicMock(),
    )
    complete_action = AsyncMock(return_value=[])
    monkeypatch.setattr(goal_interface, "complete_overworld_action", complete_action)

    forced_toolset = _toolset(context)
    assert set(forced_toolset.tools) == {"set_goal"}

    set_goal = cast("_GoalToolFunction", forced_toolset.tools["set_goal"].function)
    await set_goal(index=0, goal=goal_text)

    assert context.state.goals.goals == [
        Goal(goal=goal_text, updated_at_iteration=review_iteration)
    ]
    assert context.consume_control_handoff()
    complete_action.assert_awaited_once()
    assert set(_toolset(context).tools) == {"press_buttons", "set_goal", "navigation"}
