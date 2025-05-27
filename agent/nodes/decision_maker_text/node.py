from junjo import Node
from loguru import logger

from agent.nodes.decision_maker_text.service import DecisionMakerTextService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class DecisionMakerTextNode(Node[AgentStore]):
    """Make a decision based on the current game state in the text."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Running the text decision maker...")

        state = await store.get_state()
        service = DecisionMakerTextService(
            iteration=state.iteration,
            emulator=self.emulator,
            raw_memory=state.raw_memory,
            goals=state.goals,
            summary_memory=state.summary_memory,
            long_term_memory=state.long_term_memory,
        )

        await service.make_decision()

        await store.set_raw_memory(service.raw_memory)

        await store.set_emulator_save_state_from_emulator(self.emulator)
