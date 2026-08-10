"""Typed orchestration for the gameplay agents."""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from agent.battle.agent import run_battle
from agent.context import AgentContext
from agent.overworld.agent import run_overworld
from agent.text.agent import run_text
from agent.utils import is_battle_handler_state
from llm.usage import bind_llm_usage_updater

if TYPE_CHECKING:
    from emulator.game_state import GameState

type AgentHandler = Callable[[AgentContext], Awaitable[None]]


def select_agent_handler(game_state: GameState) -> AgentHandler:
    """Select the gameplay handler responsible for the observed state."""
    if is_battle_handler_state(game_state):
        return run_battle
    if game_state.is_text_on_screen() or game_state.map.height == 0 or game_state.map.width == 0:
        return run_text
    return run_overworld


async def dispatch_agent(context: AgentContext) -> None:
    """Settle the game and run the handler for its current gameplay domain."""
    await context.emulator.wait_for_animation_to_finish()
    await context.emulator.wait_for_animation_to_finish()
    game_state = await context.emulator.get_game_state()
    handler = select_agent_handler(game_state)
    with bind_llm_usage_updater(context.add_llm_usage):
        await handler(context)
