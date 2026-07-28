"""Business logic for make decision in the battle subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.battle_handler.nodes.make_decision.prompts import MAKE_DECISION_PROMPT
from agent.subflows.battle_handler.nodes.make_decision.schemas import MakeDecisionResponse
from llm.service import OpenAILLMService

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from memory.rolling_memory import RollingMemory

llm_service = OpenAILLMService()


async def make_decision(
    *,
    rolling_memory: RollingMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> RollingMemory:
    """Make a decision in a battle based on the current game state.

    Args:
        rolling_memory: Recent memory to update with the model response.
        state_string_builder: Formatter for the current game state.
        emulator: Running emulator used to inspect the battle and press buttons.

    Returns:
        The updated rolling memory. Model failures are logged and leave the memory unchanged.
    """
    game_state, img = await emulator.get_game_state_with_screenshot()
    state_string = state_string_builder(game_state)
    prompt = MAKE_DECISION_PROMPT.format(state=state_string, text=game_state.screen.text)
    try:
        response = await llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=MakeDecisionResponse,
        )
        rolling_memory.add_memory(content=str(response))
        for i, button in enumerate(response.buttons):
            # We skip the wait on the last press so we can go immediately to the next node.
            wait_for_animation = i < len(response.buttons) - 1
            await emulator.press_button(button, wait_for_animation=wait_for_animation)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error making decision. Skipping. {e}")
    return rolling_memory
