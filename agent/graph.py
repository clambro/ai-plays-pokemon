from junjo import Edge, Graph, RunConcurrent

from agent.conditions import AgentHandlerIs, ShouldRetrieveMemory
from agent.nodes.create_long_term_memory.node import CreateLongTermMemoryNode
from agent.nodes.dummy.node import DummyNode
from agent.nodes.prepare_agent_store.node import PrepareAgentStoreNode
from agent.nodes.retrieve_long_term_memory.node import RetrieveLongTermMemoryNode
from agent.nodes.should_retrieve_memory.node import ShouldRetrieveMemoryNode
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
    prepare_agent_store = PrepareAgentStoreNode(emulator)
    should_retrieve_memory = ShouldRetrieveMemoryNode()
    retrieve_long_term_memory = RetrieveLongTermMemoryNode(emulator)
    update_goals = UpdateGoalsNode(emulator)
    update_summary_memory = UpdateSummaryMemoryNode(emulator)
    create_long_term_memory = CreateLongTermMemoryNode(emulator)
    update_long_term_memory = UpdateLongTermMemoryNode(emulator)

    battle_handler_subflow = BattleHandlerSubflow(
        graph=build_battle_handler_subflow_graph(emulator),
        store_factory=lambda: BattleHandlerStore(BattleHandlerState()),
        emulator=emulator,
    )
    text_handler_subflow = TextHandlerSubflow(
        graph=build_text_handler_subflow_graph(emulator),
        store_factory=lambda: TextHandlerStore(TextHandlerState()),
        emulator=emulator,
    )
    overworld_handler_subflow = OverworldHandlerSubflow(
        graph=build_overworld_handler_subflow_graph(emulator),
        store_factory=lambda: OverworldHandlerStore(OverworldHandlerState()),
        emulator=emulator,
    )

    do_updates = RunConcurrent(
        name="DoUpdates",
        items=[
            update_goals,
            update_summary_memory,
            create_long_term_memory,
        ],
    )

    post_retrieval_dummy = DummyNode()

    return Graph(
        source=prepare_agent_store,
        sink=do_updates,
        edges=[
            Edge(
                prepare_agent_store,
                should_retrieve_memory,
            ),
            Edge(
                should_retrieve_memory,
                update_long_term_memory,
                ShouldRetrieveMemory(True),
            ),
            Edge(
                update_long_term_memory,
                retrieve_long_term_memory,
            ),
            Edge(
                should_retrieve_memory,
                post_retrieval_dummy,
                ShouldRetrieveMemory(False),
            ),
            Edge(
                retrieve_long_term_memory,
                post_retrieval_dummy,
            ),
            Edge(
                post_retrieval_dummy,
                overworld_handler_subflow,
                AgentHandlerIs(AgentStateHandler.OVERWORLD),
            ),
            Edge(
                post_retrieval_dummy,
                battle_handler_subflow,
                AgentHandlerIs(AgentStateHandler.BATTLE),
            ),
            Edge(
                post_retrieval_dummy,
                text_handler_subflow,
                AgentHandlerIs(AgentStateHandler.TEXT),
            ),
            Edge(
                text_handler_subflow,
                do_updates,
            ),
            Edge(
                battle_handler_subflow,
                do_updates,
            ),
            Edge(
                overworld_handler_subflow,
                do_updates,
            ),
        ],
    )
