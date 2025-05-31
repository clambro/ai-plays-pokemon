from junjo import Edge, Graph

from agent.nodes.dummy.node import DummyNode
from agent.subflows.text_handler.conditions import NeedsGenericHandling
from agent.subflows.text_handler.nodes.handle_dialog_box.node import HandleDialogBoxNode
from agent.subflows.text_handler.nodes.make_decision.node import MakeDecisionNode
from emulator.emulator import YellowLegacyEmulator


def build_text_handler_subflow_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo text handler subflow graph."""
    # Trivial for now, but will be more complex in the future.
    handle_dialog_box = HandleDialogBoxNode(emulator)
    make_decision = MakeDecisionNode(emulator)

    dummy_sink = DummyNode()

    return Graph(
        source=handle_dialog_box,
        sink=dummy_sink,
        edges=[
            Edge(handle_dialog_box, make_decision, NeedsGenericHandling(True)),
            Edge(handle_dialog_box, dummy_sink, NeedsGenericHandling(False)),
            Edge(make_decision, dummy_sink),
        ],
    )
