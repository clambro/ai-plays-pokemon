from burr.core.action import action
from loguru import logger
from agent.actions.generic_decision_maker.service import GenericDecisionMakerService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


GENERIC_DECISION_MAKER = "Generic Decision Maker"


@action.pydantic(reads=[], writes=[AgentStateParams.button_presses])
async def generic_decision_maker(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """
    Make a decision based on the current game state.
    To be used as a fallback when no other action is appropriate.
    """
    logger.info("Running the generic decision maker...")

    service = GenericDecisionMakerService(emulator)
    response = await service.make_decision()
    state.button_presses.append(response.button)
    return state
