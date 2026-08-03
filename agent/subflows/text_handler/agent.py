"""Pydantic AI text-agent construction and interaction execution."""

from typing import TYPE_CHECKING

from loguru import logger
from pydantic_ai import Agent, AgentRunError, BinaryContent, CallToolsNode
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.context import AgentContext
from agent.subflows.text_handler.prompts import build_text_decision_prompt
from agent.subflows.text_handler.tools.registry import build_text_toolset
from agent.subflows.text_handler.utils import (
    handle_text_dialog,
    is_plain_text_dialog,
    is_text_interaction_state,
)
from agent.utils import AGENT_HOOKS, build_screenshot_content
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS
from memory.rolling_memory import finalize_iteration

if TYPE_CHECKING:
    from PIL import Image

    from emulator.game_state import YellowLegacyGameState


def build_text_agent(context: AgentContext) -> Agent[AgentContext, str]:
    """Construct the Pydantic AI text agent."""
    return Agent[AgentContext, str](
        model=f"openai-responses:{MODEL}",
        name="text_agent",
        deps_type=AgentContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[build_text_toolset(context)],
        capabilities=[AGENT_HOOKS],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=REASONING_EFFORT,
            openai_prompt_cache_key="text-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )


async def run_text(context: AgentContext) -> None:
    """Handle one complete text interaction, using an agent only for decisions."""
    logger.info("Running the text handler...")
    await context.begin_iteration()
    agent_input = await _prepare_text_agent_input(context)
    if agent_input is not None:
        agent = build_text_agent(context)
        try:
            async with agent.iter(agent_input, deps=context) as agent_run:
                node = agent_run.next_node
                while not agent.is_end_node(node):
                    current_node = node
                    node = await agent_run.next(node)
                    if isinstance(current_node, CallToolsNode):
                        game_state = await context.emulator.get_game_state()
                        if not is_text_interaction_state(game_state):
                            break
        except AgentRunError as error:
            logger.warning(f"Error running text interaction. Skipping. {error}")
            return
    await finalize_iteration(context.state.rolling_memory)


async def _prepare_text_agent_input(
    context: AgentContext,
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
    context: AgentContext,
    *,
    initial_game_state: YellowLegacyGameState,
    initial_screenshot: Image.Image,
) -> list[str | BinaryContent]:
    """Build the initial multimodal input for a text-agent run."""
    return [
        build_screenshot_content(initial_screenshot),
        build_text_decision_prompt(context, initial_game_state),
    ]
