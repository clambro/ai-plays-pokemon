"""Overworld behavior test for forced periodic goal updates."""

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

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
@pytest.mark.parametrize(
    "goal_texts",
    [
        ["Heal the team.", None, None, None],
        ["Reach the next town.", "Investigate the locked building.", None, None],
        [None, " Heal the team. ", None, "Collect the nearby item."],
        [
            "Reach the next town.",
            "Investigate the locked building.",
            "Heal the team.",
            "Collect the nearby item.",
        ],
    ],
)
async def test_goal_replacement_satisfies_forced_review(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    goal_texts: list[str | None],
) -> None:
    """Nullable tool entries are filtered before replacing or reviewing stored goals."""
    review_iteration = 200
    original_goals = ["Reach the next town.", "Investigate the locked building."]
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=review_iteration,
            goals=[Goal(goal=goal, updated_at_iteration=0) for goal in original_goals],
        ),
        emulator=MagicMock(),
    )
    complete_action = AsyncMock(return_value=[])
    monkeypatch.setattr(goal_interface, "complete_overworld_action", complete_action)

    forced_toolset = _toolset(context)
    assert set(forced_toolset.tools) == {"set_goals"}

    set_goals = cast("_GoalToolFunction", forced_toolset.tools["set_goals"].function)
    arguments = forced_toolset.tools["set_goals"].function_schema.validator.validate_python(
        {"goals": goal_texts},
    )
    await set_goals(**arguments)

    assert context.state.goals == [
        Goal(goal=goal.strip(), updated_at_iteration=review_iteration)
        for goal in goal_texts
        if goal is not None
    ]
    assert context.consume_control_handoff()
    complete_action.assert_awaited_once()
    context.state = AgentState.model_validate_json(context.state.model_dump_json())
    assert set(_toolset(context).tools) == {
        "check_connection",
        "press_buttons",
        "set_goals",
        "navigation",
    }


@pytest.mark.unit
@pytest.mark.parametrize("slot_count", [0, 1, 3, 5])
def test_goal_tool_rejects_incorrect_slot_count(tmp_path: Path, slot_count: int) -> None:
    """The tool boundary requires exactly four entries, counting unused slots."""
    context = AgentContext(state=AgentState(folder=tmp_path), emulator=MagicMock())
    tool = goal_interface.build_set_goals_tool(context)

    with pytest.raises(ValidationError):
        tool.function_schema.validator.validate_python({"goals": [None] * slot_count})
