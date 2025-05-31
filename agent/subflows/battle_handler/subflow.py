from junjo import Graph, Subflow

from agent.state import AgentState, AgentStore
from agent.subflows.battle_handler.state import BattleHandlerState, BattleHandlerStore
from emulator.emulator import YellowLegacyEmulator


class BattleHandlerSubflow(Subflow[BattleHandlerState, BattleHandlerStore, AgentState, AgentStore]):
    """The battle handler subflow."""

    def __init__(
        self,
        graph: Graph,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.emulator = emulator
        super().__init__(graph)

    async def pre_run_actions(self, parent_store: AgentStore) -> BattleHandlerStore:
        """Pre run actions that initialize the subflow store from the parent store."""
        return await BattleHandlerStore.from_parent(parent_store)

    async def post_run_actions(self, parent_store: AgentStore) -> None:
        """Post run actions that update the parent store with the subflow's state."""
        state = await self.store.get_state()

        if state.agent_memory is None:
            raise ValueError("Agent memory is not set")

        await parent_store.set_agent_memory(state.agent_memory)
        await parent_store.set_emulator_save_state_from_emulator(self.emulator)
