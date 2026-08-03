"""Integration tests for shared Pydantic AI hooks."""

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

from agent import utils
from agent.context import AgentContext
from agent.state import AgentState
from agent.text.agent import build_text_agent
from llm.service import MODEL

if TYPE_CHECKING:
    from pathlib import Path

    from emulator.game_state import YellowLegacyGameState


@pytest.mark.unit
async def test_hooks_publish_accounted_reasoning_before_tool_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Publish updated usage and reasoning before the selected tool acts."""
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
                model_name=MODEL,
                provider_name="openai",
            ),
            ModelResponse(
                parts=[TextPart("The action is complete.")],
                usage=final_usage,
                model_name=MODEL,
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
    game_state = MagicMock()
    context = AgentContext(
        state=AgentState(folder=tmp_path),
        emulator=MagicMock(),
    )
    context.emulator.get_game_state = AsyncMock(return_value=game_state)

    def publish(state: AgentState, observed_state: YellowLegacyGameState) -> None:
        assert observed_state is game_state
        assert state.total_tokens == first_usage.total_tokens
        assert state.rolling_memory.current_block.content == reasoning
        events.append("publish")

    monkeypatch.setattr(utils, "update_background_from_states", publish)
    agent = build_text_agent(context)

    @agent.tool_plain
    async def test_action() -> str:
        """Perform the test action."""
        events.append("tool")
        return "done"

    with agent.override(model=FunctionModel(model_function, model_name=MODEL)):
        result = await agent.run("Use the test action.", deps=context)

    assert result.output == "The action is complete."
    assert events == ["publish", "tool"]
    assert context.state.total_tokens == first_usage.total_tokens + final_usage.total_tokens
