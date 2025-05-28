from junjo import Node
from loguru import logger

from agent.nodes.update_goals.service import UpdateGoalsService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


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
            iteration=state.iteration,
            agent_memory=state.agent_memory,
            goals=state.goals,
        )
        goals = await service.update_goals()

        await store.set_goals(goals)
        await store.set_emulator_save_state_from_emulator(self.emulator)
