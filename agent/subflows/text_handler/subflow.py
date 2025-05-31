from junjo import Graph, Subflow

from agent.state import AgentState, AgentStore
from agent.subflows.text_handler.state import TextHandlerState, TextHandlerStore
from emulator.emulator import YellowLegacyEmulator


class TextHandlerSubflow(Subflow[TextHandlerState, TextHandlerStore, AgentState, AgentStore]):
    """The text handler subflow."""

    def __init__(
        self,
        graph: Graph,
        store: TextHandlerStore,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.emulator = emulator
        super().__init__(graph, store)

    async def pre_run_actions(self, parent_store: AgentStore) -> None:
        """Pre run actions that initialize the subflow store from the parent store."""
        parent_state = await parent_store.get_state()
        await self.store.set_state_from_parent(parent_state)

    async def post_run_actions(self, parent_store: AgentStore) -> None:
        """Post run actions that update the parent store with the subflow's state."""
        state = await self.store.get_state()

        if state.agent_memory is None:
            raise ValueError("Agent memory is not set")

        await parent_store.set_agent_memory(state.agent_memory)
        await parent_store.set_emulator_save_state_from_emulator(self.emulator)
