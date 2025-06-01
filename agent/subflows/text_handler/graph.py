from junjo import Edge, Graph

from agent.nodes.dummy.node import DummyNode
from agent.subflows.text_handler.conditions import HandlerIs
from agent.subflows.text_handler.enums import TextHandler
from agent.subflows.text_handler.nodes.assign_name.node import AssignNameNode
from agent.subflows.text_handler.nodes.determine_handler.node import DetermineHandlerNode
from agent.subflows.text_handler.nodes.handle_dialog_box.node import HandleDialogBoxNode
from agent.subflows.text_handler.nodes.make_decision.node import MakeDecisionNode
from emulator.emulator import YellowLegacyEmulator


def build_text_handler_subflow_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo text handler subflow graph."""
    determine_handler = DetermineHandlerNode(emulator)
    handle_dialog_box = HandleDialogBoxNode(emulator)
    assign_name = AssignNameNode(emulator)
    make_decision = MakeDecisionNode(emulator)

    dummy_sink = DummyNode()

    return Graph(
        source=determine_handler,
        sink=dummy_sink,
        edges=[
            Edge(determine_handler, handle_dialog_box, HandlerIs(TextHandler.DIALOG_BOX)),
            Edge(determine_handler, assign_name, HandlerIs(TextHandler.NAME)),
            Edge(determine_handler, make_decision, HandlerIs(TextHandler.GENERIC)),
            Edge(determine_handler, dummy_sink, HandlerIs(None)),
            Edge(handle_dialog_box, dummy_sink),
            Edge(assign_name, dummy_sink),
            Edge(make_decision, dummy_sink),
        ],
    )
