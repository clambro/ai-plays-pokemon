from burr.core.action import action
from loguru import logger
from agent.actions.update_goals.service import UpdateGoalsService
from agent.state import AgentState, AgentStateParams


UPDATE_GOALS = "Update Goals"


@action.pydantic(
    reads=[AgentStateParams.goals, AgentStateParams.raw_memory],
    writes=[AgentStateParams.goals],
)
async def update_goals(state: AgentState) -> AgentState:
    """Update the goals based on the raw memory."""
    logger.info("Updating the goals...")

    service = UpdateGoalsService(raw_memory=state.raw_memory, goals=state.goals)
    await service.update_goals()  # Updated in place.
    return state
