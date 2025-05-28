from loguru import logger

from agent.nodes.update_long_term_memory.prompts import UPDATE_LONG_TERM_MEMORY_PROMPT
from agent.nodes.update_long_term_memory.schemas import UpdateLongTermMemoryResponse, UpdateType
from common.embedding_service import GeminiEmbeddingService
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from database.long_term_memory.repository import update_long_term_memory
from database.long_term_memory.schemas import LongTermMemoryUpdate
from emulator.emulator import YellowLegacyEmulator
from memory.agent_memory import AgentMemory


class UpdateLongTermMemoryService:
    """Service for updating long-term memory."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)
    embedding_service = GeminiEmbeddingService()

    def __init__(
        self,
        iteration: int,
        agent_memory: AgentMemory,
        goals: Goals,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.agent_memory = agent_memory
        self.goals = goals
        self.emulator = emulator

    async def update_long_term_memory(self) -> None:
        """Update long-term memory."""
        if not self.agent_memory.has_long_term_memory:
            return

        game_state = self.emulator.get_game_state()
        prompt = UPDATE_LONG_TERM_MEMORY_PROMPT.format(
            agent_memory=self.agent_memory,
            player_info=game_state.player_info,
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                prompt,
                UpdateLongTermMemoryResponse,
            )
            title_piece_map = {p.title: p for p in self.agent_memory.long_term_memory.pieces}
            for update_piece in response.pieces:
                orig_piece = title_piece_map.get(update_piece.title)
                if orig_piece is None:
                    logger.warning(
                        f"Tried to update non-existent long-term memory piece:"
                        f" {update_piece.title}. Skipping.",
                    )
                    continue
                if update_piece.update_type == UpdateType.APPEND:
                    content = f"{orig_piece.content}\n{update_piece.content}"
                else:
                    content = update_piece.content
                embedding = await self.embedding_service.get_embedding(content, update_piece.title)
                await update_long_term_memory(
                    LongTermMemoryUpdate(
                        id=orig_piece.id,
                        content=content,
                        importance=update_piece.importance,
                        iteration=self.iteration,
                        embedding=embedding,
                    ),
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error updating long-term memory. Skipping.\n{e}")
