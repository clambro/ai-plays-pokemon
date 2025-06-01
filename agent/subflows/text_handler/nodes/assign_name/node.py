from junjo import Node
from loguru import logger

from agent.subflows.text_handler.nodes.assign_name.service import AssignNameService
from agent.subflows.text_handler.state import TextHandlerStore
from emulator.emulator import YellowLegacyEmulator


class AssignNameNode(Node[TextHandlerStore]):
    """Assign a name to something in the game."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: TextHandlerStore) -> None:
        """The service for the node."""
        logger.info("Assigning a name...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")

        service = AssignNameService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            emulator=self.emulator,
        )
        raw_memory = await service.assign_name()

        await store.set_raw_memory(raw_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
