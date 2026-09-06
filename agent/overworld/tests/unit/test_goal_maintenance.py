"""Overworld behavior test for forced periodic goal updates."""

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.context import AgentContext
from agent.overworld.tools import registry
from agent.overworld.tools.set_goals import interface as goal_interface
from agent.state import AgentState
from memory.goals import Goal

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
async def test_stale_goals_allow_unchanged_review_then_restore_normal_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An unchanged full-list review satisfies required goal maintenance."""
    review_iteration = 200
    goal_texts = ["I will reach the next town.", "I will investigate the locked building."]
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=review_iteration,
            goals=[Goal(goal=goal, updated_at_iteration=0) for goal in goal_texts],
        ),
        emulator=MagicMock(),
    )
    complete_action = AsyncMock(return_value=[])
    monkeypatch.setattr(goal_interface, "complete_overworld_action", complete_action)

    forced_toolset = _toolset(context)
    assert set(forced_toolset.tools) == {"set_goals"}

    set_goals = cast("_GoalToolFunction", forced_toolset.tools["set_goals"].function)
    await set_goals(goals=goal_texts)

    assert context.state.goals == [
        Goal(goal=goal, updated_at_iteration=review_iteration) for goal in goal_texts
    ]
    assert context.consume_control_handoff()
    complete_action.assert_awaited_once()
    assert set(_toolset(context).tools) == {
        "check_connection",
        "press_buttons",
        "set_goals",
        "navigation",
    }
