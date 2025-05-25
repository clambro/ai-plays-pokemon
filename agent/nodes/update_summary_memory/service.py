from agent.nodes.update_summary_memory.prompts import UPDATE_SUMMARY_MEMORY_PROMPT
from agent.nodes.update_summary_memory.schemas import UpdateSummaryMemoryResponse
from common.constants import ITERATIONS_PER_SUMMARY_UPDATE, RAW_MEMORY_MAX_SIZE
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from long_term_memory.schemas import LongTermMemory
from raw_memory.schemas import RawMemory
from summary_memory.schemas import SummaryMemory, SummaryMemoryPiece


class UpdateSummaryMemoryService:
    """Service for updating the summary memory."""

    def __init__(
        self,
        emulator: YellowLegacyEmulator,
        iteration: int,
        raw_memory: RawMemory,
        summary_memory: SummaryMemory,
        long_term_memory: LongTermMemory,
        goals: Goals,
    ) -> None:
        self.emulator = emulator
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.summary_memory = summary_memory
        self.long_term_memory = long_term_memory
        self.goals = goals
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

    async def update_summary_memory(self) -> None:
        """Update the summary memory."""
        if self.iteration % ITERATIONS_PER_SUMMARY_UPDATE != 0:
            return
        game_state = await self.emulator.get_game_state()
        prompt = UPDATE_SUMMARY_MEMORY_PROMPT.format(
            raw_memory_max_size=RAW_MEMORY_MAX_SIZE,
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            long_term_memory=self.long_term_memory,
            player_info=game_state.player_info,
            goals=self.goals,
            iteration=self.iteration,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            prompt,
            UpdateSummaryMemoryResponse,
        )
        memories = [
            SummaryMemoryPiece(
                iteration=self.iteration,
                content=memory.description,
                importance=memory.importance,
            )
            for memory in response.memories
        ]
        self.summary_memory.append(self.iteration, *memories)
