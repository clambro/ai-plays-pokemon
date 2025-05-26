from loguru import logger

from agent.nodes.create_long_term_memory.prompts import CREATE_LONG_TERM_MEMORY_PROMPT
from agent.nodes.create_long_term_memory.schemas import CreateLongTermMemoryResponse
from common.constants import ITERATIONS_PER_LONG_TERM_MEMORY_CREATION
from common.embedding_service import GeminiEmbeddingService
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from database.long_term_memory.repository import (
    create_long_term_memory,
    get_all_long_term_memory_titles,
)
from database.long_term_memory.schemas import LongTermMemoryCreate
from emulator.emulator import YellowLegacyEmulator
from long_term_memory.schemas import LongTermMemory
from raw_memory.schemas import RawMemory
from summary_memory.schemas import SummaryMemory


class CreateLongTermMemoryService:
    """Service for creating long-term memory."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)
    embedding_service = GeminiEmbeddingService()

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        summary_memory: SummaryMemory,
        long_term_memory: LongTermMemory,
        goals: Goals,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.summary_memory = summary_memory
        self.long_term_memory = long_term_memory
        self.goals = goals
        self.emulator = emulator

    async def create_long_term_memory(self) -> None:
        """Create long-term memory."""
        if self.iteration % ITERATIONS_PER_LONG_TERM_MEMORY_CREATION != 0:
            return

        game_state = await self.emulator.get_game_state()
        titles = "\n".join(await get_all_long_term_memory_titles())
        prompt = CREATE_LONG_TERM_MEMORY_PROMPT.format(
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            long_term_memory=self.long_term_memory,
            titles=titles,
            player_info=game_state.player_info,
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                prompt,
                CreateLongTermMemoryResponse,
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
