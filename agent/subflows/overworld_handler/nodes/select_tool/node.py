from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.select_tool.service import SelectToolService
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class SelectToolNode(Node[OverworldHandlerStore]):
    """Select a tool based on the current game state in the overworld."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
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
        if state.last_critique_iteration is None:
            raise ValueError("Last critique iteration is not set")

        service = SelectToolService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            current_map=state.current_map,
            last_critique_iteration=state.last_critique_iteration,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )
        tool, raw_memory = await service.select_tool()

        await store.set_raw_memory(raw_memory)
        await store.set_tool(tool)
        await store.set_emulator_save_state_from_emulator(self.emulator)
