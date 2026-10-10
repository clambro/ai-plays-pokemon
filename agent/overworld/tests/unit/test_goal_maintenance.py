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
        map_view=MagicMock(),
        game_state=game_state,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "goal_texts",
    [
        ["Heal the team."],
        ["Reach the next town.", "Investigate the locked building."],
        [" Heal the team. ", "Collect the nearby item."],
        [
            "Reach the next town.",
            "Investigate the locked building.",
            "Heal the team.",
        ],
    ],
)
async def test_goal_replacement_satisfies_forced_review(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    goal_texts: list[str],
) -> None:
    """Replacing or retaining goals satisfies the periodic review requirement."""
    review_iteration = 200
    original_goals = ["Reach the next town.", "Investigate the locked building."]
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=review_iteration,
            last_advice_iteration=100,
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
        Goal(goal=goal.strip(), updated_at_iteration=review_iteration) for goal in goal_texts
    ]
    assert context.consume_control_handoff()
    complete_action.assert_awaited_once()
    context.state = AgentState.model_validate_json(context.state.model_dump_json())
    assert set(_toolset(context).tools) == {
        "inspect_map",
        "press_buttons",
        "set_goals",
        "navigation",
        "consult_advisor",
    }


@pytest.mark.unit
@pytest.mark.parametrize("goal_texts", [[], ["Goal"] * 4, [None]])
def test_goal_tool_rejects_invalid_list(tmp_path: Path, goal_texts: list[str | None]) -> None:
    """The tool boundary accepts one to three strings without null padding."""
    context = AgentContext(state=AgentState(folder=tmp_path), emulator=MagicMock())
    tool = goal_interface.build_set_goals_tool(context)

    with pytest.raises(ValidationError):
        tool.function_schema.validator.validate_python({"goals": goal_texts})
