from junjo import Edge, Graph

from agent.nodes.dummy.node import DummyNode
from agent.subflows.battle_handler.conditions import ToolArgsIs
from agent.subflows.battle_handler.nodes.determine_handler.node import DetermineHandlerNode
from agent.subflows.battle_handler.nodes.make_decision.node import MakeDecisionNode
from agent.subflows.battle_handler.nodes.run_tool.node import RunToolNode
from agent.subflows.battle_handler.schemas import (
    RunToolArgs,
    SwitchPokemonToolArgs,
    ThrowBallToolArgs,
    UseMoveToolArgs,
)
from emulator.emulator import YellowLegacyEmulator


def build_battle_handler_subflow_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo battle handler subflow graph."""
    determine_handler = DetermineHandlerNode(emulator)
    make_decision = MakeDecisionNode(emulator)
    run_tool = RunToolNode(emulator)
    dummy_sink = DummyNode()
    return Graph(
        source=determine_handler,
        sink=make_decision,
        edges=[
            Edge(determine_handler, make_decision, ToolArgsIs(None)),
            Edge(determine_handler, make_decision, ToolArgsIs(UseMoveToolArgs)),
            Edge(determine_handler, make_decision, ToolArgsIs(SwitchPokemonToolArgs)),
            Edge(determine_handler, make_decision, ToolArgsIs(ThrowBallToolArgs)),
            Edge(determine_handler, run_tool, ToolArgsIs(RunToolArgs)),
            Edge(make_decision, dummy_sink),
            Edge(run_tool, dummy_sink),
        ],
    )
