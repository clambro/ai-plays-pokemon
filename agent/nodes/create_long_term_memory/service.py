"""Business logic for create long term memory in the top-level agent graph."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.nodes.create_long_term_memory.prompts import CREATE_LONG_TERM_MEMORY_PROMPT
from agent.nodes.create_long_term_memory.schemas import CreateLongTermMemoryResponse
from database.long_term_memory.repository import (
    create_long_term_memory as create_long_term_memory_record,
)
from database.long_term_memory.repository import get_all_long_term_memory_titles
from database.long_term_memory.schemas import LongTermMemoryCreate
from llm.service import OpenAILLMService

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator

llm_service = OpenAILLMService()


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
        Provider and persistence failures are logged and do not escape this function.
    """
    game_state = await emulator.get_game_state()
    titles = "\n".join(await get_all_long_term_memory_titles())
    prompt = CREATE_LONG_TERM_MEMORY_PROMPT.format(
        state=state_string_builder(game_state),
        titles=titles,
    )
    try:
        response = await llm_service.get_llm_response_pydantic(
            prompt,
            CreateLongTermMemoryResponse,
        )
        for piece in response.pieces:
            title = piece.title.strip().upper().replace(" ", "_")
            await create_long_term_memory_record(
                LongTermMemoryCreate(
                    title=title,
                    content=piece.content,
                    iteration=iteration,
                ),
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error creating long-term memory. Skipping.\n{e}")
