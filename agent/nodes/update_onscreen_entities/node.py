from junjo import Node
from loguru import logger

from agent.nodes.update_onscreen_entities.service import UpdateOnscreenEntitiesService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class UpdateOnscreenEntitiesNode(Node[AgentStore]):
    """Update the onscreen entities based on the current game state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Updating the onscreen entities...")

        state = await store.get_state()
        if state.current_map is None:
            raise ValueError("Current map is not set.")

        service = UpdateOnscreenEntitiesService(
            emulator=self.emulator,
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            current_map=state.current_map,
            summary_memory=state.summary_memory,
            long_term_memory=state.long_term_memory,
        )
        await service.update_onscreen_entities()

        await store.set_emulator_save_state_from_emulator(self.emulator)
