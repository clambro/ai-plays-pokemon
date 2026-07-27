"""Business logic for critique in the overworld subflow."""

from typing import TYPE_CHECKING

from agent.subflows.overworld_handler.nodes.critique.prompts import CRITIQUE_PROMPT
from agent.subflows.overworld_handler.nodes.critique.schemas import CritiqueResponse
from llm.schemas import GEMINI_PRO_2_5
from llm.service import GeminiLLMService

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from memory.raw_memory import RawMemory


async def critique(
    *,
    iteration: int,
    raw_memory: RawMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> RawMemory:
    """Ask the critic model for overworld-specific navigation advice.

    Args:
        iteration: Current agent iteration used to timestamp the critique.
        raw_memory: Recent memory to update with the critique or provider error.
        state_string_builder: Formatter for the current overworld state and map context.
        emulator: Running emulator used to inspect the current game state.

    Returns:
        The supplied raw memory after appending the critique result.
    """
    llm_service = GeminiLLMService(GEMINI_PRO_2_5)
    game_state, screenshot = await emulator.get_game_state_with_screenshot()
    prompt = CRITIQUE_PROMPT.format(state=state_string_builder(game_state))
    try:
        response = await llm_service.get_llm_response_pydantic(
            [screenshot, prompt],
            schema=CritiqueResponse,
            thinking_tokens=1024,
        )
        raw_memory.add_memory(
            iteration=iteration,
            content=(
                f"The critic model has provided me with the following advice: {response.critique}"
            ),
        )
    except Exception as e:  # noqa: BLE001
        raw_memory.add_memory(
            iteration=iteration,
            content=f"There was an error in the critique process. {e}",
        )
    return raw_memory
