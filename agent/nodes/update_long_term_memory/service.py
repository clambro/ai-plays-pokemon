"""Business logic for update long term memory in the top-level agent graph."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.nodes.update_long_term_memory.prompts import UPDATE_LONG_TERM_MEMORY_PROMPT
from agent.nodes.update_long_term_memory.schemas import UpdateLongTermMemoryResponse, UpdateType
from database.long_term_memory.repository import update_long_term_memory as update_memory_record
from database.long_term_memory.schemas import LongTermMemoryUpdate
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from memory.long_term_memory import LongTermMemory

llm_service = GeminiLLMService(GEMINI_FLASH_2_5)


async def update_long_term_memory(
    *,
    iteration: int,
    long_term_memory: LongTermMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> None:
    """Persist model-proposed updates to loaded long-term memories.

    Args:
        iteration: Current agent iteration used to timestamp updates.
        long_term_memory: Loaded memories eligible for append or rewrite operations.
        state_string_builder: Formatter for the current game state and memory context.
        emulator: Running emulator used to inspect the current game state.

    Note:
        Missing titles and provider or persistence failures are logged and skipped.
    """
    if not long_term_memory.pieces:
        return

    game_state = await emulator.get_game_state()
    prompt = UPDATE_LONG_TERM_MEMORY_PROMPT.format(state=state_string_builder(game_state))
    try:
        response = await llm_service.get_llm_response_pydantic(
            prompt,
            UpdateLongTermMemoryResponse,
        )
        for update_piece in response.pieces:
            title = update_piece.title.strip().upper().replace(" ", "_")
            orig_piece = long_term_memory.pieces.get(title)
            if orig_piece is None:
                logger.warning(
                    f"Tried to update non-existent long-term memory piece: {title}. Skipping.",
                )
                continue
            if update_piece.update_type == UpdateType.APPEND:
                content = f"{orig_piece.content}\n{update_piece.content}"
            else:  # Rewrite.
                content = update_piece.content
            await update_memory_record(
                LongTermMemoryUpdate(
                    title=title,
                    content=content,
                    importance=update_piece.importance,
                    iteration=iteration,
                ),
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error updating long-term memory. Skipping.\n{e}")
