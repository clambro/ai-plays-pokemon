"""Press buttons node for the overworld subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.press_buttons.service import press_buttons
from agent.subflows.overworld_handler.state import OverworldHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class PressButtonsNode(Node[OverworldHandlerStore]):
    """Press buttons based on the current game state in the overworld."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the press buttons node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Pressing buttons...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")

        rolling_memory = await press_buttons(
            rolling_memory=state.rolling_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )

        await store.set_rolling_memory(rolling_memory)
