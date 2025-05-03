from burr.core.action import action
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


BUILD_AGENT_STATE = "Build Agent State"


@action.pydantic(
    # We need to be able to read and write everything in this action.
    reads=[*AgentStateParams.__members__.values()],
    writes=[*AgentStateParams.__members__.values()],
)
async def build_agent_state(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """
    The first action in the agent loop. Builds the agent state based on the emulator and the
    previous state.
    """
    state.iteration += 1
    return state
