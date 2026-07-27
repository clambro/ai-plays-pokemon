"""Business logic for update goals in the top-level agent graph."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.nodes.update_goals.prompts import UPDATE_GOALS_PROMPT
from agent.nodes.update_goals.schemas import UpdateGoalsResponse
from common.constants import ITERATIONS_PER_GOAL_UPDATE
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from memory.goals import Goals

llm_service = GeminiLLMService(GEMINI_FLASH_2_5)


async def update_goals(
    *,
    emulator: YellowLegacyEmulator,
    iteration: int,
    goals: Goals,
    state_string_builder: StateStringBuilder,
) -> Goals:
    """Update agent goals at the configured interval.

    Args:
        emulator: Running emulator used to inspect the current game state.
        iteration: Current agent iteration used to enforce the update interval.
        goals: Goal collection to mutate with the model's removals and additions.
        state_string_builder: Formatter for the current game state and memory context.

    Returns:
        The supplied goal collection after any accepted updates.
    """
    if iteration % ITERATIONS_PER_GOAL_UPDATE != 0:
        return goals

    game_state = emulator.get_game_state()
    prompt = UPDATE_GOALS_PROMPT.format(state=state_string_builder(game_state))
    try:
        response = await llm_service.get_llm_response_pydantic(
            messages=prompt,
            schema=UpdateGoalsResponse,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error updating goals. Skipping. {e}")
        return goals
    try:
        goals.remove(*response.remove)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error removing goals. Skipping. {e}")
    try:
        goals.append(*response.append)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error appending goals. Skipping. {e}")

    return goals
