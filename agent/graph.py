from junjo import Edge, Graph

from agent.conditions import AgentHandlerIs, ShouldCritique, ToolIs
from agent.nodes.build_agent_state.node import UpdateAgentStoreNode
from agent.nodes.critique.node import CritiqueNode
from agent.nodes.decision_maker_battle.node import DecisionMakerBattleNode
from agent.nodes.decision_maker_overworld.node import DecisionMakerOverworldNode
from agent.nodes.decision_maker_text.node import DecisionMakerTextNode
from agent.nodes.handle_dialog_box.node import HandleDialogBoxNode
from agent.nodes.navigation.node import NavigationNode
from agent.nodes.should_critique.node import ShouldCritiqueNode
from agent.nodes.update_current_map.node import UpdateCurrentMapNode
from agent.nodes.update_goals.node import UpdateGoalsNode
from agent.nodes.update_onscreen_entities.node import UpdateOnscreenEntitiesNode
from common.enums import AgentStateHandler, Tool
from emulator.emulator import YellowLegacyEmulator


def build_agent_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo agent graph."""
    update_agent_store = UpdateAgentStoreNode(emulator)
    update_current_map = UpdateCurrentMapNode(emulator)
    should_critique = ShouldCritiqueNode(emulator)
    critique = CritiqueNode(emulator)
    update_onscreen_entities = UpdateOnscreenEntitiesNode(emulator)
    decision_maker_overworld = DecisionMakerOverworldNode(emulator)
    decision_maker_battle = DecisionMakerBattleNode(emulator)
    decision_maker_text = DecisionMakerTextNode(emulator)
    handle_dialog_box = HandleDialogBoxNode(emulator)
    update_goals = UpdateGoalsNode(emulator)
    navigation = NavigationNode(emulator)

    return Graph(
        source=update_agent_store,
        sink=update_goals,
        edges=[
            Edge(
                update_agent_store,
                update_current_map,
                AgentHandlerIs(AgentStateHandler.OVERWORLD),
            ),
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
                navigation,
                update_goals,
            ),
            Edge(
                update_agent_store,
                decision_maker_battle,
                AgentHandlerIs(AgentStateHandler.BATTLE),
            ),
            Edge(
                update_agent_store,
                handle_dialog_box,
                AgentHandlerIs(AgentStateHandler.TEXT),
            ),
            Edge(
                handle_dialog_box,
                decision_maker_text,
                AgentHandlerIs(AgentStateHandler.TEXT),
            ),
            Edge(
                handle_dialog_box,
                update_goals,
                AgentHandlerIs(None),
            ),
            Edge(
                decision_maker_text,
                update_goals,
            ),
            Edge(
                decision_maker_overworld,
                update_goals,
                ToolIs(None),
            ),
            Edge(
                decision_maker_battle,
                update_goals,
            ),
        ],
    )
