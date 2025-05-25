from agent.nodes.create_long_term_memory.prompts import CREATE_LONG_TERM_MEMORY_PROMPT
from agent.nodes.create_long_term_memory.schemas import CreateLongTermMemoryResponse
from common.embedding_service import GeminiEmbeddingService
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from database.long_term_memory.repository import create_long_term_memory
from database.long_term_memory.schemas import LongTermMemoryCreate, LongTermMemoryRead
from emulator.emulator import YellowLegacyEmulator
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
        long_term_memory: list[LongTermMemoryRead],
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
        prompt = CREATE_LONG_TERM_MEMORY_PROMPT.format()
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
