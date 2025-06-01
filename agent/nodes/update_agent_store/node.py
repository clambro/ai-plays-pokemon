from junjo import Node
from loguru import logger

from agent.nodes.update_agent_store.service import BuildAgentStateService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class UpdateAgentStoreNode(Node[AgentStore]):
    """The first node in the agent loop. Prepares the agent store for the next iteration."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Updating agent store...")

        state = await store.get_state()
        service = BuildAgentStateService(self.emulator)

        await service.wait_for_animations()
        handler = await service.determine_handler()

        await store.set_iteration(state.iteration + 1)
        await store.set_handler(handler)

        await store.set_emulator_save_state_from_emulator(self.emulator)
