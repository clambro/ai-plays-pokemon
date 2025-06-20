from loguru import logger

from agent.subflows.battle_handler.nodes.make_decision.prompts import MAKE_DECISION_PROMPT
from agent.subflows.battle_handler.nodes.make_decision.schemas import MakeDecisionResponse
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService
from memory.raw_memory import RawMemory, RawMemoryPiece


class MakeDecisionService:
    """A service that makes decisions based on the current game state in the battle."""

    llm_service = GeminiLLMService(GEMINI_FLASH_2_5)

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
        Make a decision in a battle based on the current game state.

        :return: The raw memory with the decision added.
        """
        img = self.emulator.get_screenshot()
        game_state = self.emulator.get_game_state()
        state_string = self.state_string_builder(game_state)
        prompt = MAKE_DECISION_PROMPT.format(state=state_string, text=game_state.screen.text)
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=MakeDecisionResponse,
                prompt_name="make_battle_decision",
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

        new_game_state = self.emulator.get_game_state()
        if new_game_state.screen.tiles == game_state.screen.tiles:
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"I pressed the {response.button} button, but the screen did not change."
                        f" Have I made a mistake?"
                    ),
                ),
            )

        return self.raw_memory
