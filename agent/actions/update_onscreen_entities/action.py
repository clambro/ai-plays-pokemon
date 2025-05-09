from burr.core.action import action
from loguru import logger
from agent.actions.update_onscreen_entities.service import UpdateOnscreenEntitiesService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


UPDATE_ONSCREEN_ENTITIES = "Update Onscreen Entities"


@action.pydantic(
    reads=[AgentStateParams.folder, AgentStateParams.raw_memory, AgentStateParams.current_map],
    writes=[],
)
async def update_onscreen_entities(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """Update the onscreen entities based on the current game state."""
    logger.info("Updating the onscreen entities...")

    service = UpdateOnscreenEntitiesService(
        emulator=emulator,
        parent_folder=state.folder,
        raw_memory=state.raw_memory,
        current_map=state.current_map,
    )
    await service.update_onscreen_entities()
    return state
