from loguru import logger
from agent.actions.update_goals.service import UpdateGoalsService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator
from junjo.node import Node


class UpdateGoalsNode(Node[AgentStore]):
    """Update the goals based on the raw memory."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Updating the goals...")

        state = await store.get_state()

        service = UpdateGoalsService(
            emulator=self.emulator,
            raw_memory=state.raw_memory,
            goals=state.goals,
        )
        await service.update_goals()  # Updated in place.

        await store.set_goals(service.goals)
