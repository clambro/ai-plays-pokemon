from agent.subflows.overworld_handler.nodes.critique.prompts import CRITIQUE_PROMPT
from agent.subflows.overworld_handler.nodes.critique.schemas import CritiqueResponse
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from llm.schemas import GEMINI_PRO_2_5
from llm.service import GeminiLLMService
from memory.raw_memory import RawMemory


class CritiqueService:
    """A service that critiques the current state of the game."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.state_string_builder = state_string_builder
        self.emulator = emulator
        self.llm_service = GeminiLLMService(GEMINI_PRO_2_5)

    async def critique(self) -> RawMemory:
        """Critique the current state of the game."""
        game_state = self.emulator.get_game_state()
        screenshot = self.emulator.get_screenshot()
        prompt = CRITIQUE_PROMPT.format(state=self.state_string_builder(game_state))
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                [screenshot, prompt],
                schema=CritiqueResponse,
                prompt_name="critique_overworld_state",
                thinking_tokens=1024,
            )
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=(
                    f"The critic model has provided me with the following advice on my progress:"
                    f" {response.critique}"
                ),
            )
        except Exception as e:  # noqa: BLE001
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=f"There was an error in the critique process. {e}",
            )
        return self.raw_memory
