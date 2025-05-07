from burr.core.action import action
from loguru import logger
from agent.actions.decision_maker_overworld.service import DecisionMakerOverworldService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


DECISION_MAKER_OVERWORLD = "Decision Maker Overworld"


@action.pydantic(
    reads=[
        AgentStateParams.iteration,
        AgentStateParams.raw_memory,
        AgentStateParams.current_map,
        AgentStateParams.goals,
    ],
    writes=[AgentStateParams.buttons_pressed, AgentStateParams.raw_memory],
)
async def decision_maker_overworld(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """Make a decision based on the current game state in the overworld."""
    logger.info("Running the overworld decision maker...")
    if state.current_map is None:
        raise ValueError("Current map needs to be set before running the overworld decision maker.")

    service = DecisionMakerOverworldService(
        iteration=state.iteration,
        emulator=emulator,
        raw_memory=state.raw_memory,  # Modified in place.
        current_map=state.current_map,
        goals=state.goals,
    )
    button = await service.make_decision()
    state.buttons_pressed.append(button)
    return state
