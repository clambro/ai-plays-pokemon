from burr.core.action import action
from loguru import logger
from agent.actions.handle_dialogue_box.service import HandleDialogueBoxService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


HANDLE_DIALOGUE_BOX = "Handle Dialogue Box"


@action.pydantic(
    reads=[AgentStateParams.iteration, AgentStateParams.raw_memory],
    writes=[AgentStateParams.raw_memory, AgentStateParams.handler]
)
async def handle_dialogue_box(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """Handle reading the dialogue box if it is present."""
    logger.info("Handling the dialogue box if it is present...")

    service = HandleDialogueBoxService(
        iteration=state.iteration,
        emulator=emulator,
        raw_memory=state.raw_memory,  # Modified in place.
    )
    state.handler = await service.handle_dialogue_box()
    return state
