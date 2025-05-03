from loguru import logger
from agent.actions.generic_decision_maker.prompts import GENERIC_DECISION_MAKER_PROMPT
from agent.actions.generic_decision_maker.schemas import GenericDecisionMakerResponse
from common.gemini import Gemini, GeminiModel
from emulator.emulator import YellowLegacyEmulator


class GenericDecisionMakerService:
    """
    A service that makes decisions based on the current game state.
    Designed to be as generic as possible, and to be used as a fallback when no other service is
    appropriate.
    """

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        self.llm_service = Gemini(GeminiModel.FLASH)

    async def make_decision(self) -> GenericDecisionMakerResponse:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = self.emulator.get_screenshot()
        prompt = GENERIC_DECISION_MAKER_PROMPT
        response = await self.llm_service.get_llm_response_pydantic(
            messages=[prompt, img],
            schema=GenericDecisionMakerResponse,
        )
        logger.info(f"Generic decision maker reasoning: {response.thoughts}")
        await self.emulator.press_buttons([response.button])
        return response
