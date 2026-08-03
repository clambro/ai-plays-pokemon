"""Construction of the top-level agent graph."""

from typing import TYPE_CHECKING

from junjo import Edge, Graph, Node

from agent.conditions import AgentHandlerIs
from agent.enums import AgentStateHandler
from agent.nodes.prepare_agent_store.node import PrepareAgentStoreNode
from agent.state import AgentStore
from agent.subflows.battle_handler.node import BattleAgentNode
from agent.subflows.overworld_handler.node import OverworldAgentNode
from agent.subflows.text_handler.node import TextHandlerNode

if TYPE_CHECKING:
    from agent.context import AgentContext


class _SyncAgentStateNode(Node[AgentStore]):
    """Copy shared context state into Junjo before the workflow returns."""

    def __init__(self, context: AgentContext) -> None:
        self.context = context
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """Synchronize the completed handler activation."""
        await store.replace_state(self.context.state)


def build_agent_graph(context: AgentContext) -> Graph:
    """Build the Junjo agent graph."""
    prepare_agent_store = PrepareAgentStoreNode(context)
    sync_agent_state = _SyncAgentStateNode(context)

    battle_agent = BattleAgentNode(context)
    text_handler = TextHandlerNode(context)
    overworld_agent = OverworldAgentNode(context)

    return Graph(
        source=prepare_agent_store,
        sink=sync_agent_state,
        edges=[
            Edge(
                prepare_agent_store,
                overworld_agent,
                AgentHandlerIs(AgentStateHandler.OVERWORLD),
            ),
            Edge(
                prepare_agent_store,
                battle_agent,
                AgentHandlerIs(AgentStateHandler.BATTLE),
            ),
            Edge(prepare_agent_store, text_handler, AgentHandlerIs(AgentStateHandler.TEXT)),
            Edge(text_handler, sync_agent_state),
            Edge(battle_agent, sync_agent_state),
            Edge(overworld_agent, sync_agent_state),
        ],
    )
