"""Business logic for make decision in the battle subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.battle_handler.nodes.make_decision.prompts import MAKE_DECISION_PROMPT
from agent.subflows.battle_handler.nodes.make_decision.schemas import MakeDecisionResponse
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from memory.raw_memory import RawMemory

llm_service = GeminiLLMService(GEMINI_FLASH_2_5)


async def make_decision(
    *,
    iteration: int,
    raw_memory: RawMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> RawMemory:
    """
    Make a decision in a battle based on the current game state.

    :return: The raw memory with the decision added.
    """
    img = emulator.get_screenshot()
    game_state = emulator.get_game_state()
    state_string = state_string_builder(game_state)
    prompt = MAKE_DECISION_PROMPT.format(state=state_string, text=game_state.screen.text)
    try:
        response = await llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=MakeDecisionResponse,
            prompt_name="make_battle_decision",
        )
        raw_memory.add_memory(iteration=iteration, content=str(response))
        for i, button in enumerate(response.buttons):
            # We skip the wait on the last press so we can go immediately to the next node.
            wait_for_animation = i < len(response.buttons) - 1
            await emulator.press_button(button, wait_for_animation=wait_for_animation)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error making decision. Skipping. {e}")
    return raw_memory
