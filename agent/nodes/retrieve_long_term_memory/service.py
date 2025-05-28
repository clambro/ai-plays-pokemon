from agent.nodes.retrieve_long_term_memory.prompts import GET_RETRIEVAL_QUERY_PROMPT
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from long_term_memory.schemas import LongTermMemory
from memory.retrieval_service import MemoryRetrievalService
from raw_memory.schemas import RawMemory
from summary_memory.schemas import SummaryMemory


class RetrieveLongTermMemoryService:
    """Service for retrieving the long-term memory."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH_LITE)
    retrieval_service = MemoryRetrievalService()

    def __init__(
        self,
        emulator: YellowLegacyEmulator,
        iteration: int,
        raw_memory: RawMemory,
        summary_memory: SummaryMemory,
        prev_long_term_memory: LongTermMemory,
        goals: Goals,
    ) -> None:
        self.emulator = emulator
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.summary_memory = summary_memory
        self.prev_long_term_memory = prev_long_term_memory
        self.goals = goals

    async def retrieve_long_term_memory(self) -> LongTermMemory:
        """Retrieve the long-term memory."""
        game_state = self.emulator.get_game_state()
        screenshot = self.emulator.get_screenshot()

        prompt = GET_RETRIEVAL_QUERY_PROMPT.format(
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            long_term_memory=self.prev_long_term_memory,
            player_info=game_state.player_info,
            goals=self.goals,
        )
        query = await self.llm_service.get_llm_response([screenshot, prompt], thinking_tokens=None)

        memories = await self.retrieval_service.get_most_relevant_memories(query, self.iteration)
        return LongTermMemory(pieces=memories)
