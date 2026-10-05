"""Pydantic AI text-agent construction and interaction execution."""

from typing import TYPE_CHECKING

from loguru import logger
from pydantic_ai import Agent, AgentRunError, BinaryContent, CallToolsNode
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from pydantic_graph import End

from agent.context import AgentContext
from agent.dialog import settle_dialog
from agent.formatting.game_state import build_screenshot_content
from agent.hooks import AGENT_HOOKS
from agent.text.prompts import build_text_decision_prompt
from agent.text.tools.registry import build_text_toolset
from agent.utils import is_text_handler_state
from common.enums import ReasoningEffort
from common.prompts import SYSTEM_PROMPT
from llm.service import TIMEOUT_SECONDS, build_agent_model

if TYPE_CHECKING:
    from PIL import Image

    from emulator.game_state import GameState


def build_text_agent(
    context: AgentContext,
    initial_screen_text: str,
) -> Agent[AgentContext, str]:
    """Construct the Pydantic AI text agent."""
    return Agent[AgentContext, str](
        model=build_agent_model(),
        name="text_agent",
        deps_type=AgentContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[build_text_toolset(context, initial_screen_text)],
        capabilities=[AGENT_HOOKS],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=ReasoningEffort.MEDIUM.value,
            openai_prompt_cache_key="text-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )


async def run_text(context: AgentContext) -> None:
    """Handle text decisions until control changes or Pokemon state needs a fresh prompt."""
    await context.begin_iteration()
    settlement = await settle_dialog(context)
    await context.complete_iteration(settlement.game_state)

    if not is_text_handler_state(settlement.game_state, settlement.control_boundary):
        return
    initial_game_state = settlement.game_state
    agent_input = build_text_agent_input(
        context,
        initial_game_state=initial_game_state,
        initial_screenshot=settlement.screenshot,
    )
    agent = build_text_agent(context, initial_game_state.screen.text)
    try:
        async with agent.iter(agent_input, deps=context) as agent_run:
            node = agent_run.next_node
            while not isinstance(node, End):
                current_node = node
                node = await agent_run.next(node)
                if isinstance(current_node, CallToolsNode):
                    if context.consume_control_handoff():
                        settlement = await settle_dialog(context)
                        await context.complete_iteration(settlement.game_state)
                        break
                    (
                        game_state,
                        control_boundary,
                    ) = await context.emulator.get_game_state_with_control_boundary()
                    await context.complete_iteration(game_state)
                    # Rebuild the prompt before another decision uses stale Pokemon data.
                    if (
                        not is_text_handler_state(game_state, control_boundary)
                        or game_state.party != initial_game_state.party
                        or game_state.pc_pokemon != initial_game_state.pc_pokemon
                    ):
                        break
    except AgentRunError as error:
        logger.opt(exception=error).warning(
            "Text agent run failed; returning control to the dispatcher."
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
