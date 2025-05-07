from datetime import datetime
from agent.actions.decision_maker_text.prompts import DECISION_MAKER_TEXT_PROMPT
from agent.actions.decision_maker_text.schemas import DecisionMakerTextResponse
from common.gemini import Gemini, GeminiModel
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
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = Gemini(GeminiModel.FLASH)
        self.raw_memory = raw_memory

    async def make_decision(self) -> Button:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = await self.emulator.get_screenshot()
        prompt = DECISION_MAKER_TEXT_PROMPT.format(
            raw_memory=self.raw_memory,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=DecisionMakerTextResponse,
        )
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                timestamp=datetime.now(),
                content=response.thoughts,
            )
        )
        await self.emulator.press_buttons([response.button])
        return response.button
