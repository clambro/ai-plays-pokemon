"""Graph construction for the battle subflow."""

from typing import TYPE_CHECKING

from junjo import Edge, Graph

from agent.subflows.battle_handler.nodes.handle_subsequent_text.node import HandleSubsequentTextNode
from agent.subflows.battle_handler.nodes.make_decision.node import MakeDecisionNode

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


def build_battle_handler_subflow_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo battle handler subflow graph."""
    make_decision = MakeDecisionNode(emulator)
    handle_subsequent_text = HandleSubsequentTextNode(emulator)
    return Graph(
        source=make_decision,
        sink=handle_subsequent_text,
        edges=[Edge(make_decision, handle_subsequent_text)],
    )
