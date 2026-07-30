"""Pydantic AI overworld-agent construction and execution."""

from typing import TYPE_CHECKING

from pydantic_ai import Agent, BinaryContent, CallToolsNode, ModelResponse
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.subflows.overworld_handler.context import OverworldContext
from agent.subflows.overworld_handler.prompts import build_overworld_decision_prompt
from agent.subflows.overworld_handler.tools.registry import build_overworld_toolset
from agent.utils import build_screenshot_content
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS
from llm.usage import update_pydantic_ai_usage

if TYPE_CHECKING:
    from PIL import Image

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


async def run_overworld(context: OverworldContext) -> None:
    """Run the overworld agent until it executes one tool."""
    initial_game_state, initial_screenshot = await context.emulator.get_game_state_with_screenshot()
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
                    await update_pydantic_ai_usage(current_node.model_response)
                    accounted_responses += 1
                    if reasoning := current_node.model_response.text:
                        rolling_memory = context.state.rolling_memory
                        if rolling_memory is None:
                            raise ValueError("Rolling memory is not set")
                        rolling_memory.add_memory(
                            (
                                f"Current map: {initial_game_state.map.id.name} at coordinates"
                                f" {initial_game_state.player.coords}, facing"
                                f" {initial_game_state.player.direction.name}. {reasoning}"
                            ),
                        )
                node = await agent_run.next(node)
                if isinstance(current_node, CallToolsNode):
                    break
        finally:
            responses = [
                message
                for message in agent_run.new_messages()
                if isinstance(message, ModelResponse)
            ]
            for response in responses[accounted_responses:]:
                await update_pydantic_ai_usage(response)


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
