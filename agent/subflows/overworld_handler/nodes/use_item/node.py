from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.use_item.service import UseItemService
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class UseItemNode(Node[OverworldHandlerStore]):
    """Use an item from the inventory."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Using an item...")

        state = await store.get_state()
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")
        if state.iteration is None:
            raise ValueError("Iteration is not set")

        service = UseItemService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            emulator=self.emulator,
        )
        raw_memory = await service.use_item()

        await store.set_raw_memory(raw_memory)
