"""Pydantic AI battle-agent construction and execution."""

from typing import TYPE_CHECKING

from loguru import logger
from pydantic_ai import Agent, AgentRunError, BinaryContent, CallToolsNode
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.battle.prompts import build_battle_decision_prompt
from agent.battle.tools.registry import build_battle_toolset
from agent.context import AgentContext
from agent.utils import AGENT_HOOKS, build_screenshot_content, is_battle_handler_state
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS
from memory.rolling_memory.service import finalize_iteration

if TYPE_CHECKING:
    from PIL import Image

    from common.enums import BattleType
    from emulator.game_state import GameState


def build_battle_agent(
    context: AgentContext, battle_type: BattleType | None
) -> Agent[AgentContext, str]:
    """Construct the Pydantic AI battle agent."""
    return Agent[AgentContext, str](
        model=f"openai-responses:{MODEL}",
        name="battle_agent",
        deps_type=AgentContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[build_battle_toolset(context, battle_type)],
        capabilities=[AGENT_HOOKS],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=REASONING_EFFORT,
            openai_prompt_cache_key="battle-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )


async def run_battle(context: AgentContext) -> None:
    """Run one agent conversation until the game exits battle mode."""
    await context.begin_iteration()
    initial_game_state, initial_screenshot = await context.emulator.get_game_state_with_screenshot()
    agent = build_battle_agent(
        context,
        initial_game_state.battle.battle_type,
    )
    try:
        async with agent.iter(
            build_battle_agent_input(
                context,
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
                    if not is_battle_handler_state(game_state):
                        break
    except AgentRunError as error:
        logger.opt(exception=error).warning(
            "Battle agent run failed; returning control to the dispatcher."
        )
        return
    await finalize_iteration(context.state.rolling_memory)


def build_battle_agent_input(
    context: AgentContext,
    *,
    initial_game_state: GameState,
    initial_screenshot: Image.Image,
) -> list[str | BinaryContent]:
    """Build the initial multimodal input for a battle-agent run."""
    return [
        build_screenshot_content(initial_screenshot),
        build_battle_decision_prompt(context, initial_game_state),
    ]
