from agent.base import BaseStateWithEmulator, BaseStoreWithEmulator
from agent.state import AgentState
from common.goals import Goals
from emulator.game_state import YellowLegacyGameState
from memory.long_term_memory import LongTermMemory
from memory.raw_memory import RawMemory
from memory.summary_memory import SummaryMemory


class TextHandlerState(BaseStateWithEmulator):
    """The state used in the text handler graph workflow."""

    iteration: int | None = None
    raw_memory: RawMemory | None = None
    summary_memory: SummaryMemory | None = None
    long_term_memory: LongTermMemory | None = None
    goals: Goals | None = None
    needs_generic_handling: bool | None = None

    def to_prompt_string(self, game_state: YellowLegacyGameState) -> str:
        """Get a string representation of the agent and game state to be used in prompts."""
        return "\n\n".join(
            (
                str(self.raw_memory),
                str(self.summary_memory),
                str(self.long_term_memory),
                str(self.goals),
                game_state.player_info,
            ),
        )


class TextHandlerStore(BaseStoreWithEmulator[TextHandlerState]):
    """Concrete store for the text handler state."""

    async def set_state_from_parent(self, parent_state: AgentState) -> None:
        """Set the state from the parent state. Meant to be called at subflow initialization."""
        await self.set_state(
            {
                "iteration": parent_state.iteration,
                "raw_memory": parent_state.raw_memory,
                "summary_memory": parent_state.summary_memory,
                "long_term_memory": parent_state.long_term_memory,
                "goals": parent_state.goals,
            },
        )

    async def set_raw_memory(self, raw_memory: RawMemory) -> None:
        """Set the raw memory."""
        await self.set_state({"raw_memory": raw_memory})

    async def set_needs_generic_handling(self, needs_generic_handling: bool) -> None:
        """Set the needs generic handling."""
        await self.set_state({"needs_generic_handling": needs_generic_handling})
