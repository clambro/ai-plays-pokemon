from junjo import Node
from loguru import logger

from agent.nodes.handle_dialog_box.service import HandleDialogBoxService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class HandleDialogBoxNode(Node[AgentStore]):
    """Handle reading the dialog box if it is present."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Handling the dialog box if it is present...")

        state = await store.get_state()
        service = HandleDialogBoxService(
            iteration=state.iteration,
            emulator=self.emulator,
            agent_memory=state.agent_memory,
        )
        agent_memory, handler = await service.handle_dialog_box()

        await store.set_agent_memory(agent_memory)
        await store.set_handler(handler)
        await store.set_emulator_save_state_from_emulator(self.emulator)
