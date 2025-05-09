from burr.core.action import action
from loguru import logger
from agent.actions.decision_maker_text.service import DecisionMakerTextService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


DECISION_MAKER_TEXT = "Decision Maker Text"


@action.pydantic(
    reads=[AgentStateParams.iteration, AgentStateParams.raw_memory, AgentStateParams.goals],
    writes=[AgentStateParams.buttons_pressed, AgentStateParams.raw_memory],
)
async def decision_maker_text(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """Make a decision based on the current game state in the text."""
    logger.info("Running the text decision maker...")

    service = DecisionMakerTextService(
        iteration=state.iteration,
        emulator=emulator,
        raw_memory=state.raw_memory,  # Modified in place.
        goals=state.goals,
    )
    button = await service.make_decision()
    if button:
        state.buttons_pressed.append(button)
    return state
