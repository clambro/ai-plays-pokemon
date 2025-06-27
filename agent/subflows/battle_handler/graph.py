from junjo import Edge, Graph

from agent.subflows.battle_handler.conditions import ToolArgsIs
from agent.subflows.battle_handler.nodes.determine_handler.node import DetermineHandlerNode
from agent.subflows.battle_handler.nodes.fight_tool.node import FightToolNode
from agent.subflows.battle_handler.nodes.handle_subsequent_text.node import HandleSubsequentTextNode
from agent.subflows.battle_handler.nodes.make_decision.node import MakeDecisionNode
from agent.subflows.battle_handler.nodes.run_tool.node import RunToolNode
from agent.subflows.battle_handler.nodes.switch_pokemon_tool.node import SwitchPokemonToolNode
from agent.subflows.battle_handler.nodes.throw_ball_tool.node import ThrowBallToolNode
from agent.subflows.battle_handler.schemas import (
    FightToolArgs,
    RunToolArgs,
    SwitchPokemonToolArgs,
    ThrowBallToolArgs,
)
from emulator.emulator import YellowLegacyEmulator


def build_battle_handler_subflow_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo battle handler subflow graph."""
    determine_handler = DetermineHandlerNode(emulator)
    make_decision = MakeDecisionNode(emulator)
    fight_tool = FightToolNode(emulator)
    switch_pokemon_tool = SwitchPokemonToolNode(emulator)
    throw_ball_tool = ThrowBallToolNode(emulator)
    run_tool = RunToolNode(emulator)
    handle_subsequent_text = HandleSubsequentTextNode(emulator)
    return Graph(
        source=determine_handler,
        sink=handle_subsequent_text,
        edges=[
            Edge(determine_handler, make_decision, ToolArgsIs(None)),
            Edge(determine_handler, fight_tool, ToolArgsIs(FightToolArgs)),
            Edge(determine_handler, switch_pokemon_tool, ToolArgsIs(SwitchPokemonToolArgs)),
            Edge(determine_handler, throw_ball_tool, ToolArgsIs(ThrowBallToolArgs)),
            Edge(determine_handler, run_tool, ToolArgsIs(RunToolArgs)),
            Edge(fight_tool, handle_subsequent_text),
            Edge(switch_pokemon_tool, handle_subsequent_text),
            Edge(throw_ball_tool, handle_subsequent_text),
            Edge(run_tool, handle_subsequent_text),
            Edge(make_decision, handle_subsequent_text),
        ],
    )
