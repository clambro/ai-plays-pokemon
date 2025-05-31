from junjo import Edge, Graph

from agent.nodes.dummy.node import DummyNode
from agent.subflows.overworld_handler.conditions import ShouldCritique, ToolIs
from agent.subflows.overworld_handler.nodes.critique.node import CritiqueNode
from agent.subflows.overworld_handler.nodes.make_decision.node import MakeDecisionNode
from agent.subflows.overworld_handler.nodes.navigate.node import NavigationNode
from agent.subflows.overworld_handler.nodes.should_critique.node import ShouldCritiqueNode
from agent.subflows.overworld_handler.nodes.update_current_map.node import UpdateCurrentMapNode
from agent.subflows.overworld_handler.nodes.update_onscreen_entities.node import (
    UpdateOnscreenEntitiesNode,
)
from common.enums import Tool
from emulator.emulator import YellowLegacyEmulator


def build_overworld_handler_subflow_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the overworld handler subflow graph."""
    update_current_map = UpdateCurrentMapNode(emulator)
    should_critique = ShouldCritiqueNode(emulator)
    critique = CritiqueNode(emulator)
    update_onscreen_entities = UpdateOnscreenEntitiesNode(emulator)
    decision_maker_overworld = MakeDecisionNode(emulator)
    navigation = NavigationNode(emulator)

    dummy_sink = DummyNode()

    return Graph(
        source=update_current_map,
        sink=dummy_sink,
        edges=[
            Edge(
                update_current_map,
                update_onscreen_entities,
            ),
            Edge(
                update_onscreen_entities,
                should_critique,
            ),
            Edge(
                should_critique,
                critique,
                ShouldCritique(True),
            ),
            Edge(
                critique,
                decision_maker_overworld,
            ),
            Edge(
                should_critique,
                decision_maker_overworld,
                ShouldCritique(False),
            ),
            Edge(
                decision_maker_overworld,
                navigation,
                ToolIs(Tool.NAVIGATION),
            ),
            Edge(
                decision_maker_overworld,
                dummy_sink,
                ToolIs(None),
            ),
            Edge(
                navigation,
                dummy_sink,
            ),
        ],
    )
