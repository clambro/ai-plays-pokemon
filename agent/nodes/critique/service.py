"""Business logic for critique in the top-level agent graph."""

from typing import TYPE_CHECKING

from agent.nodes.critique.prompts import CRITIQUE_PROMPT
from agent.nodes.critique.schemas import CritiqueResponse
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
    """Critique the current state of the game."""
    llm_service = GeminiLLMService(GEMINI_PRO_2_5)
    game_state = emulator.get_game_state()
    screenshot = emulator.get_screenshot()
    prompt = CRITIQUE_PROMPT.format(
        state=state_string_builder(game_state),
        onscreen_text=game_state.screen.text,
    )
    try:
        response = await llm_service.get_llm_response_pydantic(
            [screenshot, prompt],
            schema=CritiqueResponse,
            prompt_name="general_critique",
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
