"""Consultation cooldown, recovery, and usage accounting."""

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image
from pydantic_ai import ModelResponse, RequestUsage, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from agent.context import AgentContext
from agent.overworld.tools.consult_advisor import interface, service
from agent.overworld.tools.inspect_map import service as inspection_service
from agent.overworld.tools.inspect_map.schemas import MapInspectionError
from agent.overworld.tools.registry import build_overworld_toolset
from agent.overworld.tools.set_goals import interface as goal_interface
from agent.state import AgentState
from llm.service import MODEL
from memory.goals import Goal

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from pydantic_ai import ModelMessage
    from pydantic_ai.models.function import AgentInfo


@pytest.mark.unit
@pytest.mark.parametrize("fails", [False, True])
async def test_consultation_cooldown_survives_backup_and_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    fails: bool,
) -> None:
    """Attempts consume the cooldown, including failed consultations and restored state."""
    original_goals = [Goal(goal="Reach the next town.", updated_at_iteration=0)]
    context = AgentContext(
        state=AgentState(folder=tmp_path, goals=original_goals),
        emulator=MagicMock(),
    )
    context.emulator.get_game_state_with_screenshot = AsyncMock(
        return_value=(MagicMock(), Image.new("RGB", (160, 144))),
    )
    monkeypatch.setattr(interface, "prepare_overworld_map", AsyncMock())
    monkeypatch.setattr(interface, "build_current_map_view", MagicMock())
    monkeypatch.setattr(interface, "format_overworld_state", MagicMock(return_value="state"))
    advisor = MagicMock()
    advisor.run = AsyncMock(
        side_effect=RuntimeError("Provider failed") if fails else None,
        return_value=MagicMock(
            output="Investigate the accessible entrance.",
        ),
    )
    monkeypatch.setattr(service, "build_advisor_agent", MagicMock(return_value=advisor))
    tool = interface.build_consult_advisor_tool(context)
    consult = cast("Callable[[str], Awaitable[str]]", tool.function)
    game_state = MagicMock()
    game_state.can_use_strength = False
    game_state.player.has_pokedex = False
    map_view = MagicMock()
    assert "consult_advisor" in build_overworld_toolset(context, map_view, game_state).tools

    await consult("How can I make progress?")
    assert context.state.last_advice_iteration == 0
    assert context.consume_control_handoff()
    context.state = AgentState.model_validate_json(context.state.model_dump_json())
    context.state.iteration = 99
    assert "consult_advisor" not in build_overworld_toolset(context, map_view, game_state).tools

    next_consultation_iteration = 100
    context.state.iteration = next_consultation_iteration
    assert "consult_advisor" in build_overworld_toolset(context, map_view, game_state).tools
    advisor.run.reset_mock()
    await consult("How can I make progress?")
    advisor.run.assert_awaited_once()
    assert context.state.last_advice_iteration == next_consultation_iteration
    assert context.state.goals == original_goals


@pytest.mark.unit
async def test_advisor_updates_goals_and_accounts_usage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The advisor can replace goals and account for usage across its consultation."""
    context = AgentContext(
        state=AgentState(folder=tmp_path),
        emulator=MagicMock(),
    )
    monkeypatch.setattr(
        inspection_service,
        "inspect_map",
        AsyncMock(return_value=MapInspectionError.UNVISITED_MAP),
    )
    monkeypatch.setattr(goal_interface, "complete_overworld_action", AsyncMock(return_value=[]))
    responses = iter(
        [
            ModelResponse(
                parts=[ToolCallPart("inspect_map", {"map_name": "MT_MOON_B2F"})],
                usage=RequestUsage(input_tokens=2, output_tokens=3),
                model_name=MODEL,
                provider_name="openai",
            ),
            ModelResponse(
                parts=[
                    ToolCallPart(
                        "set_goals",
                        {"goals": ["Reach the next town.", None, None]},
                    ),
                ],
                usage=RequestUsage(input_tokens=4, output_tokens=5),
                model_name=MODEL,
                provider_name="openai",
            ),
            ModelResponse(
                parts=[TextPart("Reassess the route.")],
                usage=RequestUsage(input_tokens=6, output_tokens=7),
                model_name=MODEL,
                provider_name="openai",
            ),
        ],
    )

    async def model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        del messages, info
        return next(responses)

    advisor = service.build_advisor_agent(context, MagicMock())
    with advisor.override(model=FunctionModel(model_function, model_name=MODEL)):
        result = await advisor.run("Help me decide where to go.", deps=context)

    assert result.output == "Reassess the route."
    assert context.state.goals == [Goal(goal="Reach the next town.", updated_at_iteration=0)]
    expected_tokens = 27
    assert context.state.total_tokens == expected_tokens
    assert context.state.total_cost > 0
