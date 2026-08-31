"""Pydantic AI battle-agent construction and execution."""

from typing import TYPE_CHECKING

from loguru import logger
from pydantic_ai import Agent, AgentRunError, BinaryContent, CallToolsNode
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from pydantic_graph import End

from agent.battle.formatting import is_evolution_family_caught
from agent.battle.prompts import build_battle_decision_prompt
from agent.battle.tools.registry import build_battle_toolset
from agent.context import AgentContext
from agent.dialog import settle_dialog
from agent.utils import AGENT_HOOKS, build_screenshot_content, is_battle_handler_state
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS

if TYPE_CHECKING:
    from PIL import Image

    from common.enums import BattleType
    from emulator.game_state import GameState


def build_battle_agent(
    context: AgentContext,
    battle_type: BattleType | None,
    *,
    enemy_family_caught: bool,
) -> Agent[AgentContext, str]:
    """Construct the Pydantic AI battle agent."""
    return Agent[AgentContext, str](
        model=f"openai-responses:{MODEL}",
        name="battle_agent",
        deps_type=AgentContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[
            build_battle_toolset(
                context,
                battle_type,
                enemy_family_caught=enemy_family_caught,
            )
        ],
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
    settlement = await settle_dialog(context)
    await context.complete_iteration()
    if not is_battle_handler_state(settlement.game_state):
        return
    game_state = settlement.game_state
    enemy_pokemon = game_state.battle.enemy_pokemon
    agent = build_battle_agent(
        context,
        game_state.battle.battle_type,
        enemy_family_caught=(
            enemy_pokemon is not None
            and is_evolution_family_caught(
                enemy_pokemon.pokedex_number,
                game_state.player.pokedex_caught,
            )
        ),
    )
    try:
        async with agent.iter(
            build_battle_agent_input(
                context,
                initial_game_state=settlement.game_state,
                initial_screenshot=settlement.screenshot,
            ),
            deps=context,
        ) as agent_run:
            node = agent_run.next_node
            while not isinstance(node, End):
                current_node = node
                node = await agent_run.next(node)
                if isinstance(current_node, CallToolsNode):
                    if context.consume_control_handoff():
                        break
                    await context.complete_iteration()
                    game_state = await context.emulator.get_game_state()
                    if not is_battle_handler_state(game_state):
                        break
    except AgentRunError as error:
        logger.opt(exception=error).warning(
            "Battle agent run failed; returning control to the dispatcher."
        )
        return


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
