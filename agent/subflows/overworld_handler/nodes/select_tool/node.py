"""Select tool node for the overworld subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.select_tool.service import select_tool
from agent.subflows.overworld_handler.state import OverworldHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class SelectToolNode(Node[OverworldHandlerStore]):
    """Select a tool based on the current game state in the overworld."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the select tool node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Selecting an overworld tool...")

        state = await store.get_state()
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.current_map is None:
            raise ValueError("Current map is not set")

        tool, raw_memory = await select_tool(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            current_map=state.current_map,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )

        await store.set_raw_memory(raw_memory)
        await store.set_tool(tool)
