from junjo import Node
from loguru import logger

from agent.nodes.should_critique.service import ShouldCritiqueService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class ShouldCritiqueNode(Node[AgentStore]):
    """A node that determines if the agent should critique."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Determining if the agent should critique...")

        state = await store.get_state()

        if state.handler is None:
            raise ValueError("Handler is not set.")

        service = ShouldCritiqueService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            goals=state.goals,
            iterations_since_last_critique=state.iterations_since_last_critique,
            handler=state.handler,
        )
        should_critique = await service.check_should_critique()

        await store.set_should_critique(should_critique)
