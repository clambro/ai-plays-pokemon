"""Business logic for retrieve long term memory in the top-level agent graph."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.nodes.retrieve_long_term_memory.prompts import SELECT_LONG_TERM_MEMORY_PROMPT
from agent.nodes.retrieve_long_term_memory.schemas import RetrieveLongTermMemoryResponse
from common.constants import MAX_LONG_TERM_MEMORIES_RETRIEVED
from database.long_term_memory.repository import (
    get_all_long_term_memory_titles,
    get_long_term_memories,
)
from llm.schemas import GEMINI_FLASH_LITE_2_5
from llm.service import GeminiLLMService
from memory.long_term_memory import LongTermMemory

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
        long_term_memory: Previously loaded memories returned if title selection fails.
        state_string_builder: Formatter for the current game state and memory context.
        emulator: Running emulator used to inspect the state and capture its screen.

    Returns:
        Memories selected by exact title, or the previously loaded set when selection fails.
    """
    available_titles = sorted(await get_all_long_term_memory_titles())
    if not available_titles:
        return LongTermMemory()

    game_state, screenshot = await emulator.get_game_state_with_screenshot()
    prompt = SELECT_LONG_TERM_MEMORY_PROMPT.format(
        max_memories=MAX_LONG_TERM_MEMORIES_RETRIEVED,
        state=state_string_builder(game_state),
        titles="\n".join(available_titles),
    )
    try:
        response = await llm_service.get_llm_response_pydantic(
            [screenshot, prompt],
            RetrieveLongTermMemoryResponse,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error selecting long-term memories. Returning the previous memories. {e}")
        return long_term_memory

    selected_titles = []
    for title in response.titles:
        normalized_title = title.strip().upper().replace(" ", "_")
        if normalized_title in available_titles:
            selected_titles.append(normalized_title)
    if not selected_titles:
        return LongTermMemory()

    pieces = await get_long_term_memories(selected_titles, iteration)
    return LongTermMemory(pieces={p.title: p for p in pieces})
