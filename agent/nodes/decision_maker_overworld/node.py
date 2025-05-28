from junjo import Node
from loguru import logger

from agent.nodes.decision_maker_overworld.service import DecisionMakerOverworldService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


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
                "Current map needs to be set before running the overworld decision maker.",
            )

        service = DecisionMakerOverworldService(
            iteration=state.iteration,
            emulator=self.emulator,
            agent_memory=state.agent_memory,
            current_map=state.current_map,
            goals=state.goals,
        )
        decision = await service.make_decision()

        await store.set_agent_memory(decision.agent_memory)
        await store.set_tool(decision.tool)
        await store.set_tool_args(decision.navigation_args)

        await store.set_emulator_save_state_from_emulator(self.emulator)
