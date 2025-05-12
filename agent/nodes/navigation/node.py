from loguru import logger
from agent.nodes.navigation.service import NavigationService
from agent.schemas import NavigationArgs
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator
from junjo import Node


class NavigationNode(Node[AgentStore]):
    """Navigate to the given coordinates."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Navigating to the given coordinates...")

        state = await store.get_state()
        if not state.current_map:
            raise ValueError("Current map is not set.")

        service = NavigationService(
            iteration=state.iteration,
            emulator=self.emulator,
            current_map=state.current_map,
            raw_memory=state.raw_memory,
            args=NavigationArgs.model_validate(state.tool_args),
        )
        await service.navigate()

        await store.set_current_map(service.current_map)
        await store.set_raw_memory(service.raw_memory)
