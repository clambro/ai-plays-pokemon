from agent.subflows.overworld_handler.nodes.should_critique.prompts import SHOULD_CRITIQUE_PROMPT
from agent.subflows.overworld_handler.nodes.should_critique.schemas import ShouldCritiqueResponse
from common.constants import ITERATIONS_PER_CRITIQUE_CHECK
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from memory.agent_memory import AgentMemory


class ShouldCritiqueService:
    """A service that determines if the agent should critique the current state of the game."""

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
        self.llm_service = GeminiLLMService(model=GeminiLLMEnum.FLASH_LITE)

    async def should_critique(self) -> bool:
        """Determine if the agent should critique the current state of the game."""
        if self.iteration % ITERATIONS_PER_CRITIQUE_CHECK != 0:
            return False

        game_state = self.emulator.get_game_state()
        prompt = SHOULD_CRITIQUE_PROMPT.format(
            player_info=game_state.player_info,
            agent_memory=self.agent_memory,
            goals=self.goals,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            prompt,
            schema=ShouldCritiqueResponse,
            thinking_tokens=None,
        )
        return response.should_critique
