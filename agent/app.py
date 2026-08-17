"""Typed orchestration for the gameplay agents."""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from agent.battle.agent import run_battle
from agent.context import AgentContext
from agent.overworld.agent import run_overworld
from agent.text.agent import run_text
from agent.utils import is_battle_handler_state, is_text_handler_state
from emulator.control_events import ControlBoundary, ControlHandoff
from llm.usage import bind_llm_usage_updater

if TYPE_CHECKING:
    from emulator.game_state import GameState

type AgentHandler = Callable[[AgentContext], Awaitable[None]]


def select_agent_handler(
    game_state: GameState,
    control_boundary: ControlBoundary | None,
) -> AgentHandler:
    """Select the gameplay handler responsible for the observed state."""
    if is_battle_handler_state(game_state):
        return run_battle
    if is_text_handler_state(game_state, control_boundary):
        return run_text
    return run_overworld


async def dispatch_agent(context: AgentContext) -> None:
    """Run the handler for the current decision-ready gameplay domain."""
    game_state, control_boundary = await context.emulator.get_game_state_with_control_boundary()
    await context.observe_game_state(game_state)
    handler = select_agent_handler(game_state, control_boundary)
    with bind_llm_usage_updater(context.add_llm_usage):
        try:
            await handler(context)
        except ControlHandoff:
            return
