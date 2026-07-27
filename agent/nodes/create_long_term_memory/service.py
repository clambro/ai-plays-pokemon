"""Business logic for create long term memory in the top-level agent graph."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.nodes.create_long_term_memory.prompts import CREATE_LONG_TERM_MEMORY_PROMPT
from agent.nodes.create_long_term_memory.schemas import CreateLongTermMemoryResponse
from common.embedding_service import get_embedding
from database.long_term_memory.repository import (
    create_long_term_memory as create_long_term_memory_record,
)
from database.long_term_memory.repository import get_all_long_term_memory_titles
from database.long_term_memory.schemas import LongTermMemoryCreate
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator

llm_service = GeminiLLMService(GEMINI_FLASH_2_5)


async def create_long_term_memory(
    *,
    iteration: int,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> None:
    """Create and persist long-term memories proposed by the model.

    Args:
        iteration: Current agent iteration used to timestamp new memories.
        state_string_builder: Formatter for the current game state and memory context.
        emulator: Running emulator used to inspect the current game state.

    Note:
        Provider, embedding, and persistence failures are logged and do not escape this function.
    """
    game_state = emulator.get_game_state()
    titles = "\n".join(await get_all_long_term_memory_titles())
    prompt = CREATE_LONG_TERM_MEMORY_PROMPT.format(
        state=state_string_builder(game_state),
        titles=titles,
    )
    try:
        response = await llm_service.get_llm_response_pydantic(
            prompt,
            CreateLongTermMemoryResponse,
            prompt_name="create_long_term_memory",
        )
        for piece in response.pieces:
            embedding = await get_embedding(piece.content, piece.title)
            await create_long_term_memory_record(
                LongTermMemoryCreate(
                    title=piece.title,
                    content=piece.content,
                    importance=piece.importance,
                    iteration=iteration,
                    embedding=embedding,
                ),
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error creating long-term memory. Skipping.\n{e}")
