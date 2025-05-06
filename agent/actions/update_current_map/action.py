from burr.core.action import action
from loguru import logger
from agent.actions.update_current_map.service import UpdateCurrentMapService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


UPDATE_CURRENT_MAP = "Update Current Map"


@action.pydantic(
    reads=[AgentStateParams.current_map, AgentStateParams.folder],
    writes=[AgentStateParams.current_map],
)
async def update_current_map(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """Update the current map based on the current game state."""
    logger.info("Updating the current map...")

    service = UpdateCurrentMapService(emulator=emulator, folder=state.folder)
    state.current_map = await service.update_current_map()
    return state
