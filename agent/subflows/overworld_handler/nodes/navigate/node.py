from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.navigate.service import NavigationService
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class NavigationNode(Node[OverworldHandlerStore]):
    """Navigate to the given coordinates."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Using the navigation tool...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")
        if state.current_map is None:
            raise ValueError("Current map is not set")

        service = NavigationService(
            iteration=state.iteration,
            emulator=self.emulator,
            current_map=state.current_map,
            raw_memory=state.raw_memory,
            state_string_builder=state.to_prompt_string,
        )
        current_map, raw_memory = await service.navigate()

        await store.set_current_map(current_map)
        await store.set_raw_memory(raw_memory)
