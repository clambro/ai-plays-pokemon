from loguru import logger

from agent.nodes.decision_maker_text.prompts import DECISION_MAKER_TEXT_PROMPT
from agent.nodes.decision_maker_text.schemas import DecisionMakerTextResponse
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from memory.long_term_memory import LongTermMemory
from raw_memory.schemas import RawMemory, RawMemoryPiece
from summary_memory.schemas import SummaryMemory


class DecisionMakerTextService:
    """A service that makes decisions based on the current game state in the text."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        raw_memory: RawMemory,
        goals: Goals,
        summary_memory: SummaryMemory,
        long_term_memory: LongTermMemory,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)
        self.raw_memory = raw_memory
        self.goals = goals
        self.summary_memory = summary_memory
        self.long_term_memory = long_term_memory

    async def make_decision(self) -> None:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = self.emulator.get_screenshot()
        prompt = DECISION_MAKER_TEXT_PROMPT.format(
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            long_term_memory=self.long_term_memory,
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
                content=str(response),
            ),
        )
        await self.emulator.press_buttons([response.button])
