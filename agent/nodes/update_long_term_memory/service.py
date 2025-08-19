from loguru import logger

from agent.nodes.update_long_term_memory.prompts import UPDATE_LONG_TERM_MEMORY_PROMPT
from agent.nodes.update_long_term_memory.schemas import UpdateLongTermMemoryResponse, UpdateType
from common.embedding_service import get_embedding
from common.types import StateStringBuilderT
from database.long_term_memory.repository import update_long_term_memory
from database.long_term_memory.schemas import LongTermMemoryUpdate
from emulator.emulator import YellowLegacyEmulator
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService
from memory.long_term_memory import LongTermMemory


class UpdateLongTermMemoryService:
    """Service for updating long-term memory."""

    llm_service = GeminiLLMService(GEMINI_FLASH_2_5)

    def __init__(
        self,
        iteration: int,
        long_term_memory: LongTermMemory,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.long_term_memory = long_term_memory
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def update_long_term_memory(self) -> None:
        """Update long-term memory."""
        if not self.long_term_memory.pieces:
            return

        game_state = self.emulator.get_game_state()
        prompt = UPDATE_LONG_TERM_MEMORY_PROMPT.format(state=self.state_string_builder(game_state))
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                prompt,
                UpdateLongTermMemoryResponse,
                prompt_name="update_long_term_memory",
            )
            for update_piece in response.pieces:
                orig_piece = self.long_term_memory.pieces.get(update_piece.title)
                if orig_piece is None:
                    logger.warning(
                        f"Tried to update non-existent long-term memory piece:"
                        f" {update_piece.title}. Skipping.",
                    )
                    continue
                if update_piece.update_type == UpdateType.APPEND:
                    content = f"{orig_piece.content}\n{update_piece.content}"
                else:  # Rewrite.
                    content = update_piece.content
                embedding = await get_embedding(content, update_piece.title)
                await update_long_term_memory(
                    LongTermMemoryUpdate(
                        title=update_piece.title,
                        content=content,
                        importance=update_piece.importance,
                        iteration=self.iteration,
                        embedding=embedding,
                    ),
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error updating long-term memory. Skipping.\n{e}")
