from datetime import datetime
from loguru import logger
from agent.actions.decision_maker_battle.prompts import DECISION_MAKER_BATTLE_PROMPT
from agent.actions.decision_maker_battle.schemas import DecisionMakerBattleResponse
from emulator.enums import Button
from common.gemini import Gemini, GeminiModel
from emulator.emulator import YellowLegacyEmulator
from raw_memory.schemas import RawMemory, RawMemoryPiece


class DecisionMakerBattleService:
    """A service that makes decisions based on the current game state in the battle."""

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
        img = self.emulator.get_screenshot()
        prompt = DECISION_MAKER_BATTLE_PROMPT.format(raw_memory=self.raw_memory)
        response = await self.llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=DecisionMakerBattleResponse,
        )
        logger.info(f"Battle decision maker reasoning: {response.thoughts}")
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                timestamp=datetime.now(),
                content=response.thoughts,
            )
        )
        await self.emulator.press_buttons([response.button])
        return response.button
