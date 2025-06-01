from junjo import Node
from loguru import logger

from agent.subflows.text_handler.nodes.make_decision.service import DecisionMakerTextService
from agent.subflows.text_handler.state import TextHandlerStore
from emulator.emulator import YellowLegacyEmulator


class MakeDecisionNode(Node[TextHandlerStore]):
    """Make a decision based on the current game state in the text."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: TextHandlerStore) -> None:
        """The service for the node."""
        logger.info("Running the text decision maker...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")

        service = DecisionMakerTextService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )

        raw_memory = await service.make_decision()

        await store.set_raw_memory(raw_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
