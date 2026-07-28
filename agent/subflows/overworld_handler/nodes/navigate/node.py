"""Navigate node for the overworld subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.navigate.service import NavigationService
from agent.subflows.overworld_handler.state import OverworldHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class NavigationNode(Node[OverworldHandlerStore]):
    """Navigate to the given coordinates."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the navigation node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Using the navigation tool...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")
        if state.current_map is None:
            raise ValueError("Current map is not set")

        service = NavigationService(
            iteration=state.iteration,
            emulator=self.emulator,
            current_map=state.current_map,
            rolling_memory=state.rolling_memory,
            state_string_builder=state.to_prompt_string,
        )
        current_map, rolling_memory = await service.navigate()

        await store.set_current_map(current_map)
        await store.set_rolling_memory(rolling_memory)
