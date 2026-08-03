"""Pydantic AI overworld-agent construction and execution."""

from typing import TYPE_CHECKING

from loguru import logger
from pydantic_ai import Agent, AgentRunError, BinaryContent, CallToolsNode
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.context import AgentContext
from agent.overworld.prompts import build_overworld_decision_prompt
from agent.overworld.tools.registry import build_overworld_toolset
from agent.utils import AGENT_HOOKS, build_screenshot_content, is_battle_handler_state
from common.prompts import SYSTEM_PROMPT
from database.long_term_memory.repository import get_all_long_term_memory_titles
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS
from memory.rolling_memory import finalize_iteration
from overworld_map.service import prepare_overworld_map

if TYPE_CHECKING:
    from PIL import Image

    from emulator.game_state import YellowLegacyGameState
    from overworld_map.schemas import OverworldMap


def build_overworld_agent(
    context: AgentContext,
    current_map: OverworldMap,
    available_long_term_memory_titles: list[str],
    game_state: YellowLegacyGameState,
) -> Agent[AgentContext, str]:
    """Construct the Pydantic AI overworld agent."""
    return Agent[AgentContext, str](
        model=f"openai-responses:{MODEL}",
        name="overworld_agent",
        deps_type=AgentContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[
            build_overworld_toolset(
                context,
                current_map,
                available_long_term_memory_titles,
                game_state,
            ),
        ],
        capabilities=[AGENT_HOOKS],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=REASONING_EFFORT,
            openai_prompt_cache_key="overworld-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )


async def run_overworld(
    context: AgentContext,
) -> None:
    """Run the overworld agent until the player moves or leaves the overworld."""
    logger.info("Running the overworld agent...")
    await context.begin_iteration()
    initial_game_state, initial_screenshot = await context.emulator.get_game_state_with_screenshot()
    current_map = await prepare_overworld_map(context.state.iteration, initial_game_state)
    available_long_term_memory_titles = sorted(await get_all_long_term_memory_titles())
    agent = build_overworld_agent(
        context,
        current_map,
        available_long_term_memory_titles,
        initial_game_state,
    )
    try:
        async with agent.iter(
            build_overworld_agent_input(
                context,
                current_map,
                available_long_term_memory_titles,
                initial_game_state=initial_game_state,
                initial_screenshot=initial_screenshot,
            ),
            deps=context,
        ) as agent_run:
            node = agent_run.next_node
            while not agent.is_end_node(node):
                current_node = node
                node = await agent_run.next(node)
                if isinstance(current_node, CallToolsNode):
                    game_state = await context.emulator.get_game_state()
                    if _should_end_overworld_run(initial_game_state, game_state):
                        break
    except AgentRunError as error:
        logger.warning(f"Error running overworld agent. Skipping. {error}")
        return
    await finalize_iteration(context.state.rolling_memory)


def build_overworld_agent_input(
    context: AgentContext,
    current_map: OverworldMap,
    available_long_term_memory_titles: list[str],
    *,
    initial_game_state: YellowLegacyGameState,
    initial_screenshot: Image.Image,
) -> list[str | BinaryContent]:
    """Build the multimodal input for one overworld-agent run."""
    return [
        build_screenshot_content(initial_screenshot),
        build_overworld_decision_prompt(
            context,
            current_map,
            available_long_term_memory_titles,
            initial_game_state,
        ),
    ]


def _should_end_overworld_run(
    initial_game_state: YellowLegacyGameState,
    game_state: YellowLegacyGameState,
) -> bool:
    """Check whether control should return to the dispatcher."""
    return (
        game_state.map.id != initial_game_state.map.id
        or game_state.player.coords != initial_game_state.player.coords
        or is_battle_handler_state(game_state)
        or game_state.is_text_on_screen()
        or game_state.map.height == 0
        or game_state.map.width == 0
    )
