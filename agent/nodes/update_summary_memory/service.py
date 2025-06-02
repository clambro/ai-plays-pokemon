from agent.nodes.update_summary_memory.prompts import UPDATE_SUMMARY_MEMORY_PROMPT
from agent.nodes.update_summary_memory.schemas import UpdateSummaryMemoryResponse
from common.constants import ITERATIONS_PER_SUMMARY_UPDATE, RAW_MEMORY_MAX_SIZE
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from memory.summary_memory import SummaryMemory, SummaryMemoryPiece


class UpdateSummaryMemoryService:
    """Service for updating the summary memory."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

    def __init__(
        self,
        iteration: int,
        summary_memory: SummaryMemory,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.emulator = emulator
        self.iteration = iteration
        self.summary_memory = summary_memory
        self.state_string_builder = state_string_builder

    async def update_summary_memory(self) -> SummaryMemory:
        """Update the summary memory."""
        if self.iteration % ITERATIONS_PER_SUMMARY_UPDATE != 0:
            return self.summary_memory

        game_state = self.emulator.get_game_state()
        prompt = UPDATE_SUMMARY_MEMORY_PROMPT.format(
            raw_memory_max_size=RAW_MEMORY_MAX_SIZE,
            state=self.state_string_builder(game_state),
            iteration=self.iteration,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            prompt,
            UpdateSummaryMemoryResponse,
            prompt_name="update_summary_memory",
        )
        self.summary_memory.append(
            self.iteration,
            *[
                SummaryMemoryPiece(
                    iteration=self.iteration,
                    content=memory.description,
                    importance=memory.importance,
                )
                for memory in response.memories
            ],
        )
        return self.summary_memory
