from agent.enums import AgentStateHandler
from common.constants import ITERATIONS_PER_LONG_TERM_MEMORY_RETRIEVAL
from emulator.emulator import YellowLegacyEmulator
from memory.long_term_memory import LongTermMemory


class PrepareAgentStateService:
    """Service for preparing the agent state."""

    def __init__(
        self,
        iteration: int,
        long_term_memory: LongTermMemory,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.long_term_memory = long_term_memory
        self.emulator = emulator

    async def wait_for_animations(self) -> None:
        """Wait until all animations have finished so that we can begin the Agent loop."""
        return await self.emulator.wait_for_animation_to_finish()

    async def determine_handler(self) -> AgentStateHandler:
        """Determine which handler to use based on the current game state."""
        game_state = self.emulator.get_game_state()
        if game_state.battle.is_in_battle:
            return AgentStateHandler.BATTLE
        if (
            game_state.is_text_on_screen()
            or game_state.map.height == 0  # Usually indicates a transition between cutscenes.
            or game_state.map.width == 0
        ):
            return AgentStateHandler.TEXT
        return AgentStateHandler.OVERWORLD

    async def should_retrieve_memory(
        self,
        handler: AgentStateHandler,
        previous_handler: AgentStateHandler | None,
    ) -> bool:
        """Determine if the agent should retrieve memory."""
        return (
            self.iteration % ITERATIONS_PER_LONG_TERM_MEMORY_RETRIEVAL == 0
            or not self.long_term_memory.pieces
            or {handler, previous_handler}
            in (  # When transitioning in or out of a battle.
                {AgentStateHandler.TEXT, AgentStateHandler.BATTLE},
                {AgentStateHandler.OVERWORLD, AgentStateHandler.BATTLE},
            )
        )
