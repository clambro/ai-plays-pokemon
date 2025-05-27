from loguru import logger

from agent.nodes.update_goals.prompts import UPDATE_GOALS_PROMPT
from agent.nodes.update_goals.schemas import UpdateGoalsResponse
from common.constants import ITERATIONS_PER_GOAL_UPDATE
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from long_term_memory.schemas import LongTermMemory
from raw_memory.schemas import RawMemory
from summary_memory.schemas import SummaryMemory


class UpdateGoalsService:
    """Service for updating the goals."""

    def __init__(
        self,
        emulator: YellowLegacyEmulator,
        iteration: int,
        raw_memory: RawMemory,
        goals: Goals,
        summary_memory: SummaryMemory,
        long_term_memory: LongTermMemory,
    ) -> None:
        self.emulator = emulator
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.goals = goals
        self.summary_memory = summary_memory
        self.long_term_memory = long_term_memory
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

    async def update_goals(self) -> None:
        """Update the goals based on the latest memory and actions."""
        if self.iteration % ITERATIONS_PER_GOAL_UPDATE != 0:
            return

        game_state = self.emulator.get_game_state()
        prompt = UPDATE_GOALS_PROMPT.format(
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            long_term_memory=self.long_term_memory,
            player_info=game_state.player_info,
            goals=self.goals,
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=prompt,
                schema=UpdateGoalsResponse,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error updating goals. Skipping. {e}")
            return
        try:
            self.goals.remove(*response.remove)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error removing goals. Skipping. {e}")
        try:
            self.goals.append(*response.append)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error appending goals. Skipping. {e}")
