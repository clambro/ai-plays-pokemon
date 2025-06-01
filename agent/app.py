from junjo import Workflow

from agent.graph import build_agent_graph
from agent.state import AgentState, AgentStore
from emulator.emulator import YellowLegacyEmulator


def build_agent_workflow(
    initial_state: AgentState,
    emulator: YellowLegacyEmulator,
) -> Workflow[AgentState, AgentStore]:
    """Build the top-level agent workflow."""
    return Workflow[AgentState, AgentStore](
        name="Pokemon Legacy Yellow Agent",
        graph=build_agent_graph(emulator),
        store_factory=lambda: AgentStore(initial_state),
    )
