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
            raw_memory=state.raw_memory,
            summary_memory=state.summary_memory,
            long_term_memory=state.long_term_memory,
        )

        await service.make_decision()

        await store.set_raw_memory(service.raw_memory)
