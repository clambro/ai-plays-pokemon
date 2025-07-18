from junjo import Edge, Graph

from agent.nodes.dummy.node import DummyNode
from agent.subflows.overworld_handler.conditions import ToolIs
from agent.subflows.overworld_handler.enums import OverworldTool
from agent.subflows.overworld_handler.nodes.critique.node import CritiqueNode
from agent.subflows.overworld_handler.nodes.load_map.node import LoadMapNode
from agent.subflows.overworld_handler.nodes.navigate.node import NavigationNode
from agent.subflows.overworld_handler.nodes.press_buttons.node import PressButtonsNode
from agent.subflows.overworld_handler.nodes.select_tool.node import SelectToolNode
from agent.subflows.overworld_handler.nodes.sokoban_solver.node import SokobanSolverNode
from agent.subflows.overworld_handler.nodes.swap_first_pokemon.node import SwapFirstPokemonNode
from agent.subflows.overworld_handler.nodes.update_map.node import UpdateMapNode
from emulator.emulator import YellowLegacyEmulator


def build_overworld_handler_subflow_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the overworld handler subflow graph."""
    load_map = LoadMapNode(emulator)
    critique = CritiqueNode(emulator)
    update_map = UpdateMapNode(emulator)
    select_tool = SelectToolNode(emulator)
    navigation = NavigationNode(emulator)
    press_buttons = PressButtonsNode(emulator)
    sokoban_solver = SokobanSolverNode(emulator)
    swap_first_pokemon = SwapFirstPokemonNode(emulator)

    dummy_sink = DummyNode()

    return Graph(
        source=load_map,
        sink=dummy_sink,
        edges=[
            Edge(load_map, update_map),
            Edge(update_map, select_tool),
            Edge(select_tool, press_buttons, ToolIs(OverworldTool.PRESS_BUTTONS)),
            Edge(select_tool, navigation, ToolIs(OverworldTool.NAVIGATION)),
            Edge(select_tool, swap_first_pokemon, ToolIs(OverworldTool.SWAP_FIRST_POKEMON)),
            Edge(select_tool, sokoban_solver, ToolIs(OverworldTool.SOKOBAN_SOLVER)),
            Edge(select_tool, critique, ToolIs(OverworldTool.CRITIQUE)),
            Edge(press_buttons, dummy_sink),
            Edge(navigation, dummy_sink),
            Edge(swap_first_pokemon, dummy_sink),
            Edge(sokoban_solver, dummy_sink),
            Edge(critique, dummy_sink),
        ],
    )
