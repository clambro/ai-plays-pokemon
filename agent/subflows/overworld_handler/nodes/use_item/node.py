"""Use item node for the overworld subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.use_item.service import UseItemService
from agent.subflows.overworld_handler.state import OverworldHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class UseItemNode(Node[OverworldHandlerStore]):
    """Use an item from the inventory."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the use item node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Using an item...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")

        service = UseItemService(
            rolling_memory=state.rolling_memory,
            emulator=self.emulator,
        )
        rolling_memory = await service.use_item()

        await store.set_rolling_memory(rolling_memory)
