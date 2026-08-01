"""Construction of the top-level agent graph."""

from typing import TYPE_CHECKING

from junjo import Edge, Graph, RunConcurrent

from agent.conditions import AgentHandlerIs
from agent.enums import AgentStateHandler
from agent.nodes.finalize_memory.node import FinalizeMemoryNode
from agent.nodes.prepare_agent_store.node import PrepareAgentStoreNode
from agent.nodes.update_background_stream.node import UpdateBackgroundStreamNode
from agent.subflows.battle_handler.node import BattleAgentNode
from agent.subflows.overworld_handler.node import OverworldAgentNode
from agent.subflows.text_handler.node import TextHandlerNode

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


def build_agent_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo agent graph."""
    prepare_agent_store = PrepareAgentStoreNode(emulator)
    update_background_stream = UpdateBackgroundStreamNode(emulator)
    finalize_memory = FinalizeMemoryNode()

    battle_agent = BattleAgentNode(emulator)
    text_handler = TextHandlerNode(emulator)
    overworld_agent = OverworldAgentNode(emulator)

    do_updates = RunConcurrent(
        name="DoUpdates",
        items=[update_background_stream],
    )

    return Graph(
        source=prepare_agent_store,
        sink=finalize_memory,
        edges=[
            Edge(
                prepare_agent_store,
                overworld_agent,
                AgentHandlerIs(AgentStateHandler.OVERWORLD),
            ),
            Edge(
                prepare_agent_store,
                battle_agent,
                AgentHandlerIs(AgentStateHandler.BATTLE),
            ),
            Edge(prepare_agent_store, text_handler, AgentHandlerIs(AgentStateHandler.TEXT)),
            Edge(text_handler, do_updates),
            Edge(battle_agent, do_updates),
            Edge(overworld_agent, do_updates),
            Edge(do_updates, finalize_memory),
        ],
    )
