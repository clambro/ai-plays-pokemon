from agent.subflows.overworld_handler.nodes.should_critique.prompts import SHOULD_CRITIQUE_PROMPT
from agent.subflows.overworld_handler.nodes.should_critique.schemas import ShouldCritiqueResponse
from common.constants import ITERATIONS_PER_CRITIQUE_CHECK
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator


class ShouldCritiqueService:
    """A service that determines if the agent should critique the current state of the game."""

    llm_service = GeminiLLMService(model=GeminiLLMEnum.FLASH_LITE)

    def __init__(
        self,
        iteration: int,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.state_string_builder = state_string_builder

    async def should_critique(self) -> bool:
        """Determine if the agent should critique the current state of the game."""
        if self.iteration % ITERATIONS_PER_CRITIQUE_CHECK != 0:
            return False

        game_state = self.emulator.get_game_state()
        prompt = SHOULD_CRITIQUE_PROMPT.format(state=self.state_string_builder(game_state))
        response = await self.llm_service.get_llm_response_pydantic(
            prompt,
            schema=ShouldCritiqueResponse,
            prompt_name="should_critique_overworld_state",
            thinking_tokens=None,
        )
        return response.should_critique
