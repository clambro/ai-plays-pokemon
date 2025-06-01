from junjo import Node
from loguru import logger

from agent.nodes.prepare_agent_store.service import PrepareAgentStateService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class PrepareAgentStoreNode(Node[AgentStore]):
    """
    The first node in the agent loop. Prepares the agent store for the next iteration and selects
    the appropriate handler.
    """

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Preparing agent store...")

        state = await store.get_state()
        service = PrepareAgentStateService(self.emulator)

        await service.wait_for_animations()
        handler = await service.determine_handler()

        await store.set_iteration(state.iteration + 1)
        await store.set_handler(handler)

        await store.set_emulator_save_state_from_emulator(self.emulator)
