"""Pydantic AI overworld-agent construction and execution."""

from typing import TYPE_CHECKING

from pydantic_ai import Agent, BinaryContent, CallToolsNode, ModelResponse
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.subflows.overworld_handler.context import (
    OverworldContext,
    prepare_overworld_context,
)
from agent.subflows.overworld_handler.prompts import build_overworld_decision_prompt
from agent.subflows.overworld_handler.tools.registry import build_overworld_toolset
from agent.utils import build_screenshot_content, is_battle_handler_state
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS
from llm.usage import update_pydantic_ai_usage

if TYPE_CHECKING:
    from PIL import Image

    from agent.state import AgentState
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState


def build_overworld_agent(
    context: OverworldContext,
    game_state: YellowLegacyGameState,
) -> Agent[OverworldContext, str]:
    """Construct the Pydantic AI overworld agent."""
    return Agent(
        model=f"openai-responses:{MODEL}",
        name="overworld_agent",
        deps_type=OverworldContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[build_overworld_toolset(context, game_state)],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=REASONING_EFFORT,
            openai_prompt_cache_key="overworld-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )


async def run_overworld(
    state: AgentState,
    emulator: YellowLegacyEmulator,
) -> None:
    """Run the overworld agent until the player moves or leaves the overworld."""
    initial_game_state, initial_screenshot = await emulator.get_game_state_with_screenshot()
    context = await prepare_overworld_context(
        state,
        emulator,
        initial_game_state,
    )
    agent = build_overworld_agent(context, initial_game_state)
    async with agent.iter(
        build_overworld_agent_input(
            context,
            initial_game_state=initial_game_state,
            initial_screenshot=initial_screenshot,
        ),
        deps=context,
    ) as agent_run:
        accounted_responses = 0
        try:
            node = agent_run.next_node
            while not agent.is_end_node(node):
                current_node = node
                if isinstance(current_node, CallToolsNode):
                    await _record_response_usage(context, current_node.model_response)
                    accounted_responses += 1
                    if reasoning := current_node.model_response.text:
                        context.state.rolling_memory.add_memory(reasoning)
                node = await agent_run.next(node)
                if isinstance(current_node, CallToolsNode):
                    game_state = await context.emulator.get_game_state()
                    if _should_end_overworld_run(initial_game_state, game_state):
                        break
        finally:
            responses = [
                message
                for message in agent_run.new_messages()
                if isinstance(message, ModelResponse)
            ]
            for response in responses[accounted_responses:]:
                await _record_response_usage(context, response)


def build_overworld_agent_input(
    context: OverworldContext,
    *,
    initial_game_state: YellowLegacyGameState,
    initial_screenshot: Image.Image,
) -> list[str | BinaryContent]:
    """Build the multimodal input for one overworld-agent run."""
    return [
        build_screenshot_content(initial_screenshot),
        build_overworld_decision_prompt(context, initial_game_state),
    ]


async def _record_response_usage(context: OverworldContext, response: ModelResponse) -> None:
    """Record one model response in both persistent and displayed state."""
    tokens, cost = await update_pydantic_ai_usage(response)
    context.state.total_tokens += tokens
    context.state.total_cost += cost


def _should_end_overworld_run(
    initial_game_state: YellowLegacyGameState,
    game_state: YellowLegacyGameState,
) -> bool:
    """Check whether control should return to the root workflow."""
    return (
        game_state.map.id != initial_game_state.map.id
        or game_state.player.coords != initial_game_state.player.coords
        or is_battle_handler_state(game_state)
        or game_state.is_text_on_screen()
        or game_state.map.height == 0
        or game_state.map.width == 0
    )
