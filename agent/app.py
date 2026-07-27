"""Application entry point for the Pokémon-playing agent."""

from typing import TYPE_CHECKING

from junjo import Workflow

from agent.graph import build_agent_graph
from agent.state import AgentState, AgentStore
from llm.usage import bind_llm_usage_updater

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


async def run_agent_workflow(
    initial_state: AgentState,
    emulator: YellowLegacyEmulator,
) -> AgentState:
    """Run one top-level agent workflow."""
    store = AgentStore(initial_state)
    workflow = Workflow[AgentState, AgentStore](
        name="Pokemon Yellow Legacy Agent",
        graph_factory=lambda: build_agent_graph(emulator),
        store_factory=lambda: store,
    )
    with bind_llm_usage_updater(store.add_llm_usage):
        await workflow.execute()
    return await workflow.get_state()
