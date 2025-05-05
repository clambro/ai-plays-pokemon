from burr.core.action import action
from loguru import logger
from agent.actions.determine_handler.service import DetermineHandlerService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


DETERMINE_HANDLER = "Determine Handler"


@action.pydantic(
    reads=[AgentStateParams.handler],
    writes=[AgentStateParams.handler],
)
async def determine_handler(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """Determine which handler to use based on the current game state."""
    logger.info("Determining which handler to use...")

    service = DetermineHandlerService(emulator=emulator)
    state.handler = await service.determine_handler()
    return state
