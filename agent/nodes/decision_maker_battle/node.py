from junjo import Node
from loguru import logger

from agent.nodes.decision_maker_battle.service import DecisionMakerBattleService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class DecisionMakerBattleNode(Node[AgentStore]):
    """Make a decision based on the current game state in the battle."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Running the battle decision maker...")

        state = await store.get_state()
        service = DecisionMakerBattleService(
            iteration=state.iteration,
            emulator=self.emulator,
            agent_memory=state.agent_memory,
        )

        agent_memory = await service.make_decision()

        await store.set_agent_memory(agent_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
