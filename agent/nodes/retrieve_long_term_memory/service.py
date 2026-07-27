"""Business logic for retrieve long term memory in the top-level agent graph."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.nodes.retrieve_long_term_memory.prompts import GET_RETRIEVAL_QUERY_PROMPT
from llm.schemas import GEMINI_FLASH_LITE_2_5
from llm.service import GeminiLLMService
from memory.long_term_memory import LongTermMemory
from memory.retrieval_service import get_most_relevant_memories

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator

llm_service = GeminiLLMService(GEMINI_FLASH_LITE_2_5)


async def retrieve_long_term_memory(
    *,
    iteration: int,
    long_term_memory: LongTermMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> LongTermMemory:
    """Retrieve long-term memories relevant to the current game state.

    Args:
        iteration: Current agent iteration used for retrieval recency.
        long_term_memory: Previously loaded memories returned if query generation fails.
        state_string_builder: Formatter for the current game state and memory context.
        emulator: Running emulator used to inspect the state and capture its screen.

    Returns:
        Relevant long-term memories, or the previously loaded set when query generation fails.
    """
    game_state = emulator.get_game_state()
    screenshot = emulator.get_screenshot()

    prompt = GET_RETRIEVAL_QUERY_PROMPT.format(state=state_string_builder(game_state))
    try:
        query = await llm_service.get_llm_response(
            [screenshot, prompt],
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error in the retrieval query. Returning the previous memories. {e}")
        return long_term_memory

    pieces = await get_most_relevant_memories(query, iteration)
    return LongTermMemory(pieces={p.title: p for p in pieces})
