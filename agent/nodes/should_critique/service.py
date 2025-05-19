from agent.nodes.should_critique.prompts import SHOULD_CRITIQUE_PROMPT
from agent.nodes.should_critique.schemas import ShouldCritiqueResponse
from common.constants import MIN_ITERATIONS_PER_CRITIQUE
from common.gemini import Gemini, GeminiModel
from common.goals import Goals
from emulator.emulator import YellowLegacyEmulator
from overworld_map.schemas import OverworldMap
from raw_memory.schemas import RawMemory


class ShouldCritiqueService:
    """A service that determines if the agent should critique the current state of the game."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        current_map: OverworldMap,
        goals: Goals,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.goals = goals
        self.emulator = emulator
        self.llm_service = Gemini(model=GeminiModel.FLASH_LITE)

    async def should_critique(self) -> bool:
        """Determine if the agent should critique the current state of the game."""
        if self.iteration % MIN_ITERATIONS_PER_CRITIQUE != 0:
            return False

        game_state = await self.emulator.get_game_state()
        prompt = SHOULD_CRITIQUE_PROMPT.format(
            player_info=game_state.player_info,
            raw_memory=self.raw_memory,
            goals=self.goals,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            prompt,
            schema=ShouldCritiqueResponse,
            thinking_tokens=None,
        )
        return response.should_critique
