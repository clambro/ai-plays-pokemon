from loguru import logger

from agent.nodes.create_long_term_memory.prompts import CREATE_LONG_TERM_MEMORY_PROMPT
from agent.nodes.create_long_term_memory.schemas import CreateLongTermMemoryResponse
from common.embedding_service import GeminiEmbeddingService
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from database.long_term_memory.repository import (
    create_long_term_memory,
    get_all_long_term_memory_titles,
)
from database.long_term_memory.schemas import LongTermMemoryCreate
from emulator.emulator import YellowLegacyEmulator


class CreateLongTermMemoryService:
    """Service for creating long-term memory."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)
    embedding_service = GeminiEmbeddingService()

    def __init__(
        self,
        iteration: int,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def create_long_term_memory(self) -> None:
        """Create long-term memory."""
        game_state = self.emulator.get_game_state()
        titles = "\n".join(await get_all_long_term_memory_titles())
        prompt = CREATE_LONG_TERM_MEMORY_PROMPT.format(
            state=self.state_string_builder(game_state),
            titles=titles,
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                prompt,
                CreateLongTermMemoryResponse,
                prompt_name="create_long_term_memory",
            )
            for piece in response.pieces:
                embedding = await self.embedding_service.get_embedding(piece.content, piece.title)
                await create_long_term_memory(
                    LongTermMemoryCreate(
                        title=piece.title,
                        content=piece.content,
                        importance=piece.importance,
                        iteration=self.iteration,
                        embedding=embedding,
                    ),
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error creating long-term memory. Skipping.\n{e}")
