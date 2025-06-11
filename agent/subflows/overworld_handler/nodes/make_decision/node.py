from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.make_decision.service import MakeDecisionService
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class MakeDecisionNode(Node[OverworldHandlerStore]):
    """Make a decision based on the current game state in the overworld."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Running the overworld decision maker...")

        state = await store.get_state()
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")
        if state.iteration is None:
            raise ValueError("Iteration is not set")

        service = MakeDecisionService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            current_map=state.current_map,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )
        decision = await service.make_decision()

        await store.set_raw_memory(decision.raw_memory)
        await store.set_tool(decision.tool)
        await store.set_tool_args(decision.navigation_args)

        await store.set_emulator_save_state_from_emulator(self.emulator)
