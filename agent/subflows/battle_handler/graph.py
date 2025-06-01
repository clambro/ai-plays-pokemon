from junjo import Graph

from agent.subflows.battle_handler.nodes.make_decision.node import MakeDecisionNode
from emulator.emulator import YellowLegacyEmulator


def build_battle_handler_subflow_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo battle handler subflow graph."""
    # Trivial for now, but will be more complex in the future.
    make_decision = MakeDecisionNode(emulator)
    return Graph(
        source=make_decision,
        sink=make_decision,
        edges=[],
    )
