from agent.graph import build_agent_graph
from agent.state import AgentState, AgentStore
from junjo.workflow import Workflow

from emulator.emulator import YellowLegacyEmulator


def build_agent_workflow(
    initial_state: AgentState,
    emulator: YellowLegacyEmulator,
) -> Workflow:
    """Build the top-level agent workflow."""
    initial_store = AgentStore(initial_state)
    return Workflow[AgentState, AgentStore](
        name="Top-Level Agent Workflow",
        graph=build_agent_graph(emulator),
        store=initial_store,
    )
