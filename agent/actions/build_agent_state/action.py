from burr.core.action import action
from agent.state import AgentState, AgentStateParams
from emulator.context import get_emulator


BUILD_AGENT_STATE = "Build Agent State"


@action(
    # We need to be able to read and write everything in this action.
    reads=[*AgentStateParams.__members__.values()],
    writes=[*AgentStateParams.__members__.values()],
)
async def build_agent_state(state: AgentState) -> AgentState:
    """
    The first action in the agent loop. Builds the agent state based on the emulator and the
    previous state.
    """
    emulator = get_emulator()
    if not emulator:
        raise RuntimeError("No emulator instance available in the current context")

    state.iteration += 1
    state.game_state = emulator.game_state
    state.screenshot = emulator.take_screenshot()
    return state
