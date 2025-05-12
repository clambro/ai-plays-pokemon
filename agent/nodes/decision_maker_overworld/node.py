from loguru import logger
from agent.nodes.decision_maker_overworld.service import DecisionMakerOverworldService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator
from junjo import Node


class DecisionMakerOverworldNode(Node[AgentStore]):
    """Make a decision based on the current game state in the overworld."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Running the overworld decision maker...")

        state = await store.get_state()
        if state.current_map is None:
            raise ValueError(
                "Current map needs to be set before running the overworld decision maker."
            )

        service = DecisionMakerOverworldService(
            iteration=state.iteration,
            emulator=self.emulator,
            raw_memory=state.raw_memory,
            current_map=state.current_map,
            goals=state.goals,
        )
        tool, args = await service.make_decision()

        await store.set_raw_memory(service.raw_memory)
        await store.set_tool(tool)
        await store.set_tool_args(args)
