from junjo import Node
from loguru import logger

from agent.nodes.prepare_agent_store.service import PrepareAgentStateService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class PrepareAgentStoreNode(Node[AgentStore]):
    """
    The first node in the agent loop. Prepares the agent store for the next iteration by selecting
    the appropriate handler and determining if the agent should retrieve memory.
    """

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Preparing agent store...")

        state = await store.get_state()
        service = PrepareAgentStateService(
            iterations_since_last_ltm_retrieval=state.iterations_since_last_ltm_retrieval,
            long_term_memory=state.long_term_memory,
            emulator=self.emulator,
        )

        await service.wait_for_animations()
        handler = await service.determine_handler()
        should_retrieve_memory = await service.should_retrieve_memory(
            handler=handler,
            previous_handler=state.handler,
        )

        await store.set_iteration(state.iteration + 1)
        await store.set_iterations_since_last_critique(state.iterations_since_last_critique + 1)
        await store.set_previous_handler(state.handler)
        await store.set_handler(handler)
        await store.set_should_retrieve_memory(should_retrieve_memory)
        await store.set_iterations_since_last_ltm_retrieval(
            state.iterations_since_last_ltm_retrieval + 1  # Is set to zero in the retrieval step.
        )
