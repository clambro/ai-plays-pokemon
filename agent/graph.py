from junjo import Edge, Graph

from agent.conditions import AgentHandlerIs
from agent.nodes.create_long_term_memory.node import CreateLongTermMemoryNode
from agent.nodes.retrieve_long_term_memory.node import RetrieveLongTermMemoryNode
from agent.nodes.update_agent_store.node import UpdateAgentStoreNode
from agent.nodes.update_goals.node import UpdateGoalsNode
from agent.nodes.update_long_term_memory.node import UpdateLongTermMemoryNode
from agent.nodes.update_summary_memory.node import UpdateSummaryMemoryNode
from agent.subflows.battle_handler.graph import build_battle_handler_subflow_graph
from agent.subflows.battle_handler.state import BattleHandlerState, BattleHandlerStore
from agent.subflows.battle_handler.subflow import BattleHandlerSubflow
from agent.subflows.overworld_handler.graph import build_overworld_handler_subflow_graph
from agent.subflows.overworld_handler.state import OverworldHandlerState, OverworldHandlerStore
from agent.subflows.overworld_handler.subflow import OverworldHandlerSubflow
from agent.subflows.text_handler.graph import build_text_handler_subflow_graph
from agent.subflows.text_handler.state import TextHandlerState, TextHandlerStore
from agent.subflows.text_handler.subflow import TextHandlerSubflow
from common.enums import AgentStateHandler
from emulator.emulator import YellowLegacyEmulator


def build_agent_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Junjo agent graph."""
    update_agent_store = UpdateAgentStoreNode(emulator)
    retrieve_long_term_memory = RetrieveLongTermMemoryNode(emulator)
    update_goals = UpdateGoalsNode(emulator)
    update_summary_memory = UpdateSummaryMemoryNode(emulator)
    create_long_term_memory = CreateLongTermMemoryNode(emulator)
    update_long_term_memory = UpdateLongTermMemoryNode(emulator)

    battle_handler_subflow = BattleHandlerSubflow(
        graph=build_battle_handler_subflow_graph(emulator),
        store=BattleHandlerStore(BattleHandlerState()),
        emulator=emulator,
    )
    text_handler_subflow = TextHandlerSubflow(
        graph=build_text_handler_subflow_graph(emulator),
        store=TextHandlerStore(TextHandlerState()),
        emulator=emulator,
    )
    overworld_handler_subflow = OverworldHandlerSubflow(
        graph=build_overworld_handler_subflow_graph(emulator),
        store=OverworldHandlerStore(OverworldHandlerState()),
        emulator=emulator,
    )

    return Graph(
        source=update_agent_store,
        sink=update_summary_memory,
        edges=[
            Edge(
                update_agent_store,
                retrieve_long_term_memory,
            ),
            Edge(
                retrieve_long_term_memory,
                overworld_handler_subflow,
                AgentHandlerIs(AgentStateHandler.OVERWORLD),
            ),
            Edge(
                retrieve_long_term_memory,
                battle_handler_subflow,
                AgentHandlerIs(AgentStateHandler.BATTLE),
            ),
            Edge(
                retrieve_long_term_memory,
                text_handler_subflow,
                AgentHandlerIs(AgentStateHandler.TEXT),
            ),
            Edge(
                text_handler_subflow,
                update_goals,
            ),
            Edge(
                battle_handler_subflow,
                update_goals,
            ),
            Edge(
                overworld_handler_subflow,
                update_goals,
            ),
            Edge(
                update_goals,
                create_long_term_memory,
            ),
            Edge(
                create_long_term_memory,
                update_long_term_memory,
            ),
            Edge(
                update_long_term_memory,
                update_summary_memory,
            ),
        ],
    )
