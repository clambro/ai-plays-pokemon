from junjo.graph import Graph
from junjo.edge import Edge

from agent.actions.build_agent_state.action import UpdateAgentStoreNode
from agent.actions.decision_maker_overworld.action import DecisionMakerOverworldNode
from agent.actions.decision_maker_battle.action import DecisionMakerBattleNode
from agent.actions.decision_maker_text.action import DecisionMakerTextNode
from agent.actions.handle_dialog_box.action import HandleDialogBoxNode
from agent.actions.update_current_map.action import UpdateCurrentMapNode
from agent.actions.update_goals.action import UpdateGoalsNode
from agent.actions.update_onscreen_entities.action import UpdateOnscreenEntitiesNode
from common.enums import AgentStateHandler
from emulator.emulator import YellowLegacyEmulator
from agent.conditions import AgentHandlerIs


def build_agent_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo agent graph."""
    update_agent_store = UpdateAgentStoreNode(emulator)
    update_current_map = UpdateCurrentMapNode(emulator)
    update_onscreen_entities = UpdateOnscreenEntitiesNode(emulator)
    decision_maker_overworld = DecisionMakerOverworldNode(emulator)
    decision_maker_battle = DecisionMakerBattleNode(emulator)
    decision_maker_text = DecisionMakerTextNode(emulator)
    handle_dialog_box = HandleDialogBoxNode(emulator)
    update_goals = UpdateGoalsNode(emulator)

    return Graph(
        source=update_agent_store,
        sink=update_goals,  # TODO: Will probably need a dummy sink node eventually.
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
                decision_maker_overworld,
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
            ),
            Edge(
                decision_maker_battle,
                update_goals,
            ),
        ],
    )
