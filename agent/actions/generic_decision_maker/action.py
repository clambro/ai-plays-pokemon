from burr.core.action import action
from loguru import logger
from agent.actions.generic_decision_maker.service import GenericDecisionMakerService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


GENERIC_DECISION_MAKER = "Generic Decision Maker"


@action.pydantic(
    reads=[AgentStateParams.iteration, AgentStateParams.raw_memory],
    writes=[AgentStateParams.buttons_pressed, AgentStateParams.raw_memory],
)
async def generic_decision_maker(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """
    Make a decision based on the current game state.
    To be used as a fallback when no other action is appropriate.
    """
    logger.info("Running the generic decision maker...")

    service = GenericDecisionMakerService(
        iteration=state.iteration,
        emulator=emulator,
        raw_memory=state.raw_memory,  # Modified in place.
    )
    response = await service.make_decision()
    state.buttons_pressed.append(response.button)
    return state
