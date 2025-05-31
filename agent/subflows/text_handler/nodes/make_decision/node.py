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
        if state.agent_memory is None:
            raise ValueError("Agent memory is not set")
        if state.goals is None:
            raise ValueError("Goals are not set")

        service = DecisionMakerTextService(
            iteration=state.iteration,
            emulator=self.emulator,
            agent_memory=state.agent_memory,
            goals=state.goals,
        )

        agent_memory = await service.make_decision()

        await store.set_agent_memory(agent_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
