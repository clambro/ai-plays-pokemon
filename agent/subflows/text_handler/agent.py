"""Pydantic AI text-agent construction and interaction execution."""

from typing import TYPE_CHECKING

from pydantic_ai import Agent, BinaryContent, CallToolsNode, ModelResponse
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.subflows.text_handler.context import TextContext
from agent.subflows.text_handler.prompts import build_text_decision_prompt
from agent.subflows.text_handler.tools.registry import build_text_toolset
from agent.subflows.text_handler.utils import (
    handle_text_dialog,
    is_plain_text_dialog,
    is_text_interaction_state,
)
from agent.utils import build_screenshot_content
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS
from llm.usage import update_pydantic_ai_usage

if TYPE_CHECKING:
    from PIL import Image

    from emulator.game_state import YellowLegacyGameState


def build_text_agent(context: TextContext) -> Agent[TextContext, str]:
    """Construct the Pydantic AI text agent."""
    return Agent(
        model=f"openai-responses:{MODEL}",
        name="text_agent",
        deps_type=TextContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[build_text_toolset(context)],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=REASONING_EFFORT,
            openai_prompt_cache_key="text-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )


async def run_text(context: TextContext) -> None:
    """Handle one complete text interaction, using an agent only for decisions."""
    agent_input = await _prepare_text_agent_input(context)
    if agent_input is None:
        return

    agent = build_text_agent(context)
    async with agent.iter(
        agent_input,
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
                    if not is_text_interaction_state(game_state):
                        break
        finally:
            responses = [
                message
                for message in agent_run.new_messages()
                if isinstance(message, ModelResponse)
            ]
            for response in responses[accounted_responses:]:
                await _record_response_usage(context, response)


async def _prepare_text_agent_input(
    context: TextContext,
) -> list[str | BinaryContent] | None:
    """Drain ordinary dialog and prepare input if a decision remains."""
    game_state = await context.emulator.get_game_state()
    if is_plain_text_dialog(game_state):
        await handle_text_dialog(context)

    initial_game_state, initial_screenshot = await context.emulator.get_game_state_with_screenshot()
    if not is_text_interaction_state(initial_game_state):
        return None
    return build_text_agent_input(
        context,
        initial_game_state=initial_game_state,
        initial_screenshot=initial_screenshot,
    )


def build_text_agent_input(
    context: TextContext,
    *,
    initial_game_state: YellowLegacyGameState,
    initial_screenshot: Image.Image,
) -> list[str | BinaryContent]:
    """Build the initial multimodal input for a text-agent run."""
    return [
        build_screenshot_content(initial_screenshot),
        build_text_decision_prompt(context, initial_game_state),
    ]


async def _record_response_usage(context: TextContext, response: ModelResponse) -> None:
    """Record one model response in both persistent and displayed state."""
    tokens, cost = await update_pydantic_ai_usage(response)
    context.state.total_tokens += tokens
    context.state.total_cost += cost
