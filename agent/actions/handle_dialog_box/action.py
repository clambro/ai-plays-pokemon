from burr.core.action import action
from loguru import logger
from agent.actions.handle_dialog_box.service import HandleDialogBoxService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


HANDLE_DIALOG_BOX = "Handle Dialog Box"


@action.pydantic(
    reads=[AgentStateParams.iteration, AgentStateParams.raw_memory],
    writes=[AgentStateParams.raw_memory, AgentStateParams.handler],
)
async def handle_dialog_box(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """Handle reading the dialog box if it is present."""
    logger.info("Handling the dialog box if it is present...")

    service = HandleDialogBoxService(
        iteration=state.iteration,
        emulator=emulator,
        raw_memory=state.raw_memory,  # Modified in place.
    )
    state.handler = await service.handle_dialog_box()
    return state
