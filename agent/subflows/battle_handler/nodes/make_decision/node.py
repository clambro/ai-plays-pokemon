from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.make_decision.service import MakeDecisionService
from agent.subflows.battle_handler.state import BattleHandlerStore
from emulator.emulator import YellowLegacyEmulator


class MakeDecisionNode(Node[BattleHandlerStore]):
    """Make a decision based on the current game state in the battle."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Running the battle decision maker...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.agent_memory is None:
            raise ValueError("Agent memory is not set")

        service = MakeDecisionService(
            iteration=state.iteration,
            agent_memory=state.agent_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )

        agent_memory = await service.make_decision()

        await store.set_agent_memory(agent_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
