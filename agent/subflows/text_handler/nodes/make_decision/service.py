from loguru import logger

from agent.subflows.text_handler.nodes.make_decision.prompts import DECISION_MAKER_TEXT_PROMPT
from agent.subflows.text_handler.nodes.make_decision.schemas import DecisionMakerTextResponse
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from llm.schemas import GEMINI_FLASH_LITE_2_5
from llm.service import GeminiLLMService
from memory.raw_memory import RawMemory, RawMemoryPiece


class DecisionMakerTextService:
    """A service that makes decisions based on the current game state in the text."""

    llm_service = GeminiLLMService(GEMINI_FLASH_LITE_2_5)

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
            buttons = (
                [str(b) for b in response.buttons]
                if isinstance(response.buttons, list)
                else [str(response.buttons)]
            )
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=f"{response.thoughts} Pressed the following buttons: {buttons}",
                ),
            )
            for b in buttons:
                await self.emulator.press_buttons(b)
                if self._check_for_state_change():
                    break

        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")

        return self.raw_memory

    def _check_for_state_change(self) -> bool:
        """Check if the movement triggered a state change to dialog or a battle."""
        game_state = self.emulator.get_game_state()
        return not game_state.is_text_on_screen() or game_state.battle.is_in_battle
