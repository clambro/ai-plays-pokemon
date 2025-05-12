from loguru import logger
from agent.nodes.update_goals.prompts import UPDATE_GOALS_PROMPT
from agent.nodes.update_goals.schemas import UpdateGoalsResponse
from common.gemini import Gemini, GeminiModel
from common.goals import Goals
from raw_memory.schemas import RawMemory
from emulator.emulator import YellowLegacyEmulator


class UpdateGoalsService:
    """Service for updating the goals."""

    def __init__(self, emulator: YellowLegacyEmulator, raw_memory: RawMemory, goals: Goals) -> None:
        self.emulator = emulator
        self.raw_memory = raw_memory
        self.goals = goals
        self.llm_service = Gemini(GeminiModel.FLASH)

    async def update_goals(self) -> None:
        """Update the goals based on the latest memory and actions."""
        game_state = await self.emulator.get_game_state()
        prompt = UPDATE_GOALS_PROMPT.format(
            raw_memory=self.raw_memory,
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
