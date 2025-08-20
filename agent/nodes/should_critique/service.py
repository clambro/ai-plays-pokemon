from loguru import logger

from agent.enums import AgentStateHandler
from agent.nodes.should_critique.prompts import SHOULD_CRITIQUE_PROMPT
from agent.nodes.should_critique.schemas import ShouldCritiqueResponse
from common.constants import (
    ITERATIONS_PER_GENERIC_CRITIQUE_CHECK,
    MIN_ITERATIONS_PER_CRITIQUE,
)
from llm.schemas import GEMINI_FLASH_LITE_2_5
from llm.service import GeminiLLMService
from memory.goals import Goals
from memory.raw_memory import RawMemory


class ShouldCritiqueService:
    """Service for determining if the agent should critique."""

    llm_service = GeminiLLMService(GEMINI_FLASH_LITE_2_5)

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        goals: Goals,
        iterations_since_last_critique: int,
        handler: AgentStateHandler,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.goals = goals
        self.iterations_since_last_critique = iterations_since_last_critique
        self.handler = handler

    async def check_should_critique(self) -> bool:
        """Check if the agent should critique by looking for loops in the raw memory."""
        if (
            # The Overworld Handler has its own critique prompt with map-specific information.
            self.handler == AgentStateHandler.OVERWORLD
            or self.iteration % ITERATIONS_PER_GENERIC_CRITIQUE_CHECK != 0
            or self.iterations_since_last_critique < MIN_ITERATIONS_PER_CRITIQUE
        ):
            return False
        try:
            prompt = SHOULD_CRITIQUE_PROMPT.format(
                raw_memory=self.raw_memory,
                goals=self.goals,
            )
            response = await self.llm_service.get_llm_response_pydantic(
                prompt,
                ShouldCritiqueResponse,
                prompt_name="should_critique",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error checking if the agent should critique. Assuming not.\n{e}")
            return False
        else:
            return response.is_stuck
