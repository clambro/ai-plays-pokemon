from burr.core.action import action
from loguru import logger
from agent.actions.decision_maker_battle.service import DecisionMakerBattleService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


DECISION_MAKER_BATTLE = "Decision Maker Battle"


@action.pydantic(
    reads=[AgentStateParams.iteration, AgentStateParams.raw_memory],
    writes=[AgentStateParams.buttons_pressed, AgentStateParams.raw_memory],
)
async def decision_maker_battle(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """Make a decision based on the current game state in the battle."""
    logger.info("Running the battle decision maker...")

    service = DecisionMakerBattleService(
        iteration=state.iteration,
        emulator=emulator,
        raw_memory=state.raw_memory,  # Modified in place.
    )
    response = await service.make_decision()
    state.buttons_pressed.append(response.button)
    return state
