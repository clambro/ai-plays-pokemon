"""Pydantic AI text-agent construction and interaction execution."""

from typing import TYPE_CHECKING

from loguru import logger
from pydantic_ai import Agent, AgentRunError, BinaryContent, CallToolsNode
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from pydantic_graph import End

from agent.context import AgentContext
from agent.dialog import settle_dialog
from agent.text.prompts import build_text_decision_prompt
from agent.text.tools.registry import build_text_toolset
from agent.utils import AGENT_HOOKS, build_screenshot_content, is_text_handler_state
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS

if TYPE_CHECKING:
    from PIL import Image

    from emulator.game_state import GameState


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
    await context.begin_iteration()
    agent_input = await _prepare_text_agent_input(context)
    if agent_input is not None:
        agent = build_text_agent(context)
        try:
            async with agent.iter(agent_input, deps=context) as agent_run:
                node = agent_run.next_node
                while not isinstance(node, End):
                    current_node = node
                    node = await agent_run.next(node)
                    if isinstance(current_node, CallToolsNode):
                        if context.consume_control_handoff():
                            break
                        await context.complete_iteration()
                        (
                            game_state,
                            control_boundary,
                        ) = await context.emulator.get_game_state_with_control_boundary()
                        if not is_text_handler_state(game_state, control_boundary):
                            break
        except AgentRunError as error:
            logger.opt(exception=error).warning(
                "Text agent run failed; returning control to the dispatcher."
            )
            return


async def _prepare_text_agent_input(
    context: AgentContext,
) -> list[str | BinaryContent] | None:
    """Drain ordinary dialog and prepare input if a decision remains."""
    settlement = await settle_dialog(context)
    await context.complete_iteration()

    if not is_text_handler_state(settlement.game_state, settlement.control_boundary):
        return None
    return build_text_agent_input(
        context,
        initial_game_state=settlement.game_state,
        initial_screenshot=settlement.screenshot,
    )


def build_text_agent_input(
    context: AgentContext,
    *,
    initial_game_state: GameState,
    initial_screenshot: Image.Image,
) -> list[str | BinaryContent]:
    """Build the initial multimodal input for a text-agent run."""
    return [
        build_screenshot_content(initial_screenshot),
        build_text_decision_prompt(context, initial_game_state),
    ]
