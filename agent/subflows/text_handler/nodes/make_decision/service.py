from loguru import logger

from agent.subflows.text_handler.nodes.make_decision.prompts import DECISION_MAKER_TEXT_PROMPT
from agent.subflows.text_handler.nodes.make_decision.schemas import DecisionMakerTextResponse
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory, RawMemoryPiece


class DecisionMakerTextService:
    """A service that makes decisions based on the current game state in the text."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

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

    async def make_decision(self) -> RawMemory:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = self.emulator.get_screenshot()
        game_state = self.emulator.get_game_state()
        state_string = self.state_string_builder(game_state)
        prompt = DECISION_MAKER_TEXT_PROMPT.format(
            state=state_string,
            text=game_state.screen.text,
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=DecisionMakerTextResponse,
                prompt_name="make_text_decision",
            )
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=str(response),
                ),
            )
            await self.emulator.press_buttons([response.button])
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")

        return self.raw_memory
