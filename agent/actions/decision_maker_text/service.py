from datetime import datetime

from loguru import logger
from agent.actions.decision_maker_text.prompts import DECISION_MAKER_TEXT_PROMPT
from agent.actions.decision_maker_text.schemas import DecisionMakerTextResponse
from common.gemini import Gemini, GeminiModel
from common.goals import Goals
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
from raw_memory.schemas import RawMemory, RawMemoryPiece


class DecisionMakerTextService:
    """A service that makes decisions based on the current game state in the text."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        raw_memory: RawMemory,
        goals: Goals,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = Gemini(GeminiModel.FLASH)
        self.raw_memory = raw_memory
        self.goals = goals

    async def make_decision(self) -> None:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = await self.emulator.get_screenshot()
        prompt = DECISION_MAKER_TEXT_PROMPT.format(
            raw_memory=self.raw_memory,
            goals=self.goals,
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=DecisionMakerTextResponse,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")
            return None
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                timestamp=datetime.now(),
                content=str(response),
            )
        )
        await self.emulator.press_buttons([response.button])
