from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.press_buttons.service import PressButtonsService
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class PressButtonsNode(Node[OverworldHandlerStore]):
    """Press buttons based on the current game state in the overworld."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Pressing buttons...")

        state = await store.get_state()
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")
        if state.iteration is None:
            raise ValueError("Iteration is not set")

        service = PressButtonsService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )
        raw_memory = await service.press_buttons()

        await store.set_raw_memory(raw_memory)
