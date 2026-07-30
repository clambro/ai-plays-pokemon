"""Graph construction for the overworld subflow."""

from typing import TYPE_CHECKING

from junjo import Edge, Graph

from agent.subflows.overworld_handler.node import OverworldAgentNode
from agent.subflows.overworld_handler.nodes.load_map.node import LoadMapNode
from agent.subflows.overworld_handler.nodes.update_map.node import UpdateMapNode

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


def build_overworld_handler_subflow_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the overworld handler subflow graph."""
    load_map = LoadMapNode(emulator)
    update_map = UpdateMapNode(emulator)
    overworld_agent = OverworldAgentNode(emulator)

    return Graph(
        source=load_map,
        sink=overworld_agent,
        edges=[
            Edge(load_map, update_map),
            Edge(update_map, overworld_agent),
        ],
    )
