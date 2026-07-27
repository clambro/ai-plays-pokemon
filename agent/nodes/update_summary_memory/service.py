"""Business logic for update summary memory in the top-level agent graph."""

from typing import TYPE_CHECKING

from agent.nodes.update_summary_memory.prompts import UPDATE_SUMMARY_MEMORY_PROMPT
from agent.nodes.update_summary_memory.schemas import UpdateSummaryMemoryResponse
from common.constants import ITERATIONS_PER_SUMMARY_UPDATE, RAW_MEMORY_MAX_SIZE
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService
from memory.summary_memory import SummaryMemory, SummaryMemoryPiece

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator

llm_service = GeminiLLMService(GEMINI_FLASH_2_5)


async def update_summary_memory(
    *,
    iteration: int,
    summary_memory: SummaryMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> SummaryMemory:
    """Update rolling summary memory at the configured interval.

    Args:
        iteration: Current agent iteration used to enforce the interval and timestamp memories.
        summary_memory: Summary collection to mutate with the model's response.
        state_string_builder: Formatter for the current game state and memory context.
        emulator: Running emulator used to inspect the current game state.

    Returns:
        The supplied summary memory after any generated additions.
    """
    if iteration % ITERATIONS_PER_SUMMARY_UPDATE != 0:
        return summary_memory

    game_state = await emulator.get_game_state()
    prompt = UPDATE_SUMMARY_MEMORY_PROMPT.format(
        raw_memory_max_size=RAW_MEMORY_MAX_SIZE,
        state=state_string_builder(game_state),
        iteration=iteration,
    )
    response = await llm_service.get_llm_response_pydantic(
        prompt,
        UpdateSummaryMemoryResponse,
    )
    summary_memory.add_memories(
        iteration,
        *[
            SummaryMemoryPiece(
                iteration=iteration,
                content=memory.description,
                importance=memory.importance,
            )
            for memory in response.memories
        ],
    )
    return summary_memory
