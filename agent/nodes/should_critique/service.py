"""Business logic for should critique in the top-level agent graph."""

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from memory.goals import Goals
    from memory.raw_memory import RawMemory

llm_service = GeminiLLMService(GEMINI_FLASH_LITE_2_5)


async def should_critique(
    *,
    iteration: int,
    raw_memory: RawMemory,
    goals: Goals,
    iterations_since_last_critique: int,
    handler: AgentStateHandler,
) -> bool:
    """Check whether the agent appears stuck and should request a critique.

    Args:
        iteration: Current agent iteration used to enforce the check interval.
        raw_memory: Recent actions inspected for repeated behavior.
        goals: Current goals supplied to the detection prompt.
        iterations_since_last_critique: Iterations elapsed since the previous critique.
        handler: Active top-level handler.

    Returns:
        Whether the generic critic should run. Provider failures default to ``False``.
    """
    if (
        # The Overworld Handler has its own critique prompt with map-specific information.
        handler == AgentStateHandler.OVERWORLD
        or iteration % ITERATIONS_PER_GENERIC_CRITIQUE_CHECK != 0
        or iterations_since_last_critique < MIN_ITERATIONS_PER_CRITIQUE
    ):
        return False
    try:
        prompt = SHOULD_CRITIQUE_PROMPT.format(
            raw_memory=raw_memory,
            goals=goals,
        )
        response = await llm_service.get_llm_response_pydantic(
            prompt,
            ShouldCritiqueResponse,
            prompt_name="should_critique",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error checking if the agent should critique. Assuming not.\n{e}")
        return False
    return response.is_stuck
