from agent.nodes.retrieve_long_term_memory.prompts import GET_RETRIEVAL_QUERY_PROMPT
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from memory.long_term_memory import LongTermMemory
from memory.retrieval_service import MemoryRetrievalService


class RetrieveLongTermMemoryService:
    """Service for retrieving the long-term memory."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH_LITE)
    retrieval_service = MemoryRetrievalService()

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

    async def retrieve_long_term_memory(self) -> LongTermMemory:
        """Retrieve the long-term memory."""
        game_state = self.emulator.get_game_state()
        screenshot = self.emulator.get_screenshot()

        prompt = GET_RETRIEVAL_QUERY_PROMPT.format(state=self.state_string_builder(game_state))
        query = await self.llm_service.get_llm_response(
            [screenshot, prompt],
            prompt_name="get_retrieval_query",
        )

        pieces = await self.retrieval_service.get_most_relevant_memories(query, self.iteration)
        return LongTermMemory(pieces={p.title: p for p in pieces})
