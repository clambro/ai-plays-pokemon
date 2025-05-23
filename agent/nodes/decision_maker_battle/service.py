from loguru import logger

from agent.nodes.decision_maker_battle.prompts import DECISION_MAKER_BATTLE_PROMPT
from agent.nodes.decision_maker_battle.schemas import DecisionMakerBattleResponse
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from raw_memory.schemas import RawMemory, RawMemoryPiece
from summary_memory.schemas import SummaryMemory


class DecisionMakerBattleService:
    """A service that makes decisions based on the current game state in the battle."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        raw_memory: RawMemory,
        summary_memory: SummaryMemory,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)
        self.raw_memory = raw_memory
        self.summary_memory = summary_memory

    async def make_decision(self) -> None:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = await self.emulator.get_screenshot()
        prompt = DECISION_MAKER_BATTLE_PROMPT.format(
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=DecisionMakerBattleResponse,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")
            return None
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=str(response),
            ),
        )
        await self.emulator.press_buttons([response.button])
