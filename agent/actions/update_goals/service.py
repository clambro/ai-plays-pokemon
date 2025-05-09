from agent.actions.update_goals.prompts import UPDATE_GOALS_PROMPT
from agent.actions.update_goals.schemas import UpdateGoalsResponse
from common.gemini import Gemini, GeminiModel
from common.goals import Goals
from raw_memory.schemas import RawMemory


class UpdateGoalsService:
    """Service for updating the goals."""

    def __init__(self, raw_memory: RawMemory, goals: Goals) -> None:
        self.raw_memory = raw_memory
        self.goals = goals
        self.llm_service = Gemini(GeminiModel.FLASH)

    async def update_goals(self) -> Goals:
        """Update the goals based on the latest memory and actions."""
        prompt = UPDATE_GOALS_PROMPT.format(
            raw_memory=self.raw_memory,
            goals=self.goals,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            messages=prompt,
            schema=UpdateGoalsResponse,
        )
        goals = self.goals.model_copy()
        goals.remove(*response.remove)
        goals.append(*response.append)
        return goals
