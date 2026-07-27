"""Business logic for prepare agent store in the top-level agent graph."""

from typing import TYPE_CHECKING

from agent.enums import AgentStateHandler
from common.constants import ITERATIONS_PER_LONG_TERM_MEMORY_RETRIEVAL

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from memory.long_term_memory import LongTermMemory


async def wait_for_animations(emulator: YellowLegacyEmulator) -> None:
    """
    Wait until all animations have finished so that we can begin the Agent loop.

    We run the check twice to be absolutely sure. Some cutscenes have a slight delay between
    actions, and missing that can cause weird downstream issues.
    """
    await emulator.wait_for_animation_to_finish()
    await emulator.wait_for_animation_to_finish()


async def determine_handler(emulator: YellowLegacyEmulator) -> AgentStateHandler:
    """Determine which handler to use based on the current game state."""
    game_state = emulator.get_game_state()
    # The nickname screen after catching a Pokemon is considered a battle state by the game,
    # but we need to route it to the text handler instead.
    if game_state.battle.is_in_battle and not game_state.is_naming_screen():
        return AgentStateHandler.BATTLE
    if (
        game_state.is_text_on_screen()
        or game_state.map.height == 0  # Usually indicates a transition between cutscenes.
        or game_state.map.width == 0
    ):
        return AgentStateHandler.TEXT
    return AgentStateHandler.OVERWORLD


async def should_retrieve_memory(
    iterations_since_last_ltm_retrieval: int,
    long_term_memory: LongTermMemory,
) -> bool:
    """Determine if the agent should retrieve memory."""
    return (
        iterations_since_last_ltm_retrieval >= ITERATIONS_PER_LONG_TERM_MEMORY_RETRIEVAL
        or not long_term_memory.pieces
    )
