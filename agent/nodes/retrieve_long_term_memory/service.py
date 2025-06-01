from agent.nodes.retrieve_long_term_memory.prompts import GET_RETRIEVAL_QUERY_PROMPT
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilder
from emulator.emulator import YellowLegacyEmulator
from memory.agent_memory import AgentMemory
from memory.retrieval_service import MemoryRetrievalService


class RetrieveLongTermMemoryService:
    """Service for retrieving the long-term memory."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH_LITE)
    retrieval_service = MemoryRetrievalService()

    def __init__(
        self,
        iteration: int,
        agent_memory: AgentMemory,
        state_string_builder: StateStringBuilder,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.agent_memory = agent_memory
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def retrieve_long_term_memory(self) -> AgentMemory:
        """Retrieve the long-term memory."""
        game_state = self.emulator.get_game_state()
        screenshot = self.emulator.get_screenshot()

        prompt = GET_RETRIEVAL_QUERY_PROMPT.format(state=self.state_string_builder(game_state))
        query = await self.llm_service.get_llm_response([screenshot, prompt], thinking_tokens=None)

        memories = await self.retrieval_service.get_most_relevant_memories(query, self.iteration)
        self.agent_memory.replace_long_term_memory(memories)

        return self.agent_memory
