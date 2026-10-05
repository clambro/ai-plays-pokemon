"""Behavior tests for shared Pydantic AI hooks."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import (
    ModelMessage,
    ModelResponse,
    RequestUsage,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from agent import hooks
from agent.context import AgentContext
from agent.overworld.tools.swap_first_pokemon.interface import build_swap_first_pokemon_tool
from agent.overworld.tools.use_item.interface import build_use_item_tool
from agent.state import AgentState
from agent.text.agent import build_text_agent
from emulator.control_events import ControlHandoff

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from pydantic_ai import Tool
    from pydantic_ai.capabilities import ValidatedToolArgs

    from agent.overworld.tools.utils import OverworldToolResult

TEST_MODEL = "gpt-6-luna"


@pytest.mark.unit
async def test_hooks_account_reasoning_before_tool_execution(tmp_path: Path) -> None:
    """Account for usage and reasoning before the selected tool acts."""
    reasoning = "I will use the test action."
    first_usage = RequestUsage(input_tokens=2, output_tokens=3)
    final_usage = RequestUsage(input_tokens=4, output_tokens=5)
    responses = iter(
        (
            ModelResponse(
                parts=[
                    TextPart(reasoning),
                    ToolCallPart("test_action"),
                ],
                usage=first_usage,
                model_name=TEST_MODEL,
                provider_name="openai",
            ),
            ModelResponse(
                parts=[TextPart("The action is complete.")],
                usage=final_usage,
                model_name=TEST_MODEL,
                provider_name="openai",
            ),
        ),
    )

    async def model_function(
        messages: list[ModelMessage],
        agent_info: AgentInfo,
    ) -> ModelResponse:
        del messages, agent_info
        return next(responses)

    events: list[str] = []
    context = AgentContext(
        state=AgentState(folder=tmp_path),
        emulator=MagicMock(),
    )
    initial_screen = MagicMock(pokemon_list_source=None, is_bag_menu=False)
    agent = build_text_agent(context, initial_screen)

    @agent.tool_plain
    async def test_action() -> str:
        """Perform the test action."""
        assert context.state.total_tokens == first_usage.total_tokens
        assert context.state.rolling_memory.current_block.content == reasoning
        assert [entry.content for entry in context.state.public_log.entries] == [reasoning]
        events.append("tool")
        return "done"

    with agent.override(model=FunctionModel(model_function, model_name=TEST_MODEL)):
        result = await agent.run("Use the test action.", deps=context)

    assert result.output == "The action is complete."
    assert events == ["tool"]
    assert context.state.total_tokens == first_usage.total_tokens + final_usage.total_tokens


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tool_factory", "arguments"),
    [
        pytest.param(build_use_item_tool, {"inventory_slot": 0}, id="use-item"),
        pytest.param(build_swap_first_pokemon_tool, {"party_slot": 1}, id="swap-first-pokemon"),
    ],
)
async def test_menu_tool_handoff_reaches_dispatcher(
    tool_factory: Callable[[AgentContext], Tool[AgentContext]],
    arguments: dict[str, int],
    tmp_path: Path,
) -> None:
    """Request dispatcher handoff without recording an ordinary menu-action failure."""
    game_state = MagicMock()
    game_state.inventory.items = [MagicMock()]
    game_state.party = [MagicMock(), MagicMock()]
    game_state.is_text_on_screen.return_value = False
    game_state.battle.is_in_battle = False
    game_state.screen.is_bag_menu = False
    emulator = MagicMock()
    emulator.get_game_state = AsyncMock(return_value=game_state)
    emulator.press_button = AsyncMock(side_effect=ControlHandoff)
    context = AgentContext(state=AgentState(folder=tmp_path), emulator=emulator)
    tool = tool_factory(context)
    action: Callable[..., Awaitable[OverworldToolResult]] = tool.function

    async def handler(args: ValidatedToolArgs) -> OverworldToolResult:
        del args
        return await action(**arguments)

    await hooks.handle_control_handoff(
        MagicMock(deps=context),
        call=MagicMock(),
        tool_def=MagicMock(),
        args={},
        handler=handler,
    )

    assert context.consume_control_handoff()
    assert not context.state.rolling_memory.current_block.content
