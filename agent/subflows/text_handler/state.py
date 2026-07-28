"""State models for the text subflow."""

from typing import TYPE_CHECKING

from junjo import BaseState, BaseStore

from agent.subflows.text_handler.enums import TextHandler
from memory.goals import Goals
from memory.long_term_memory import LongTermMemory
from memory.rolling_memory import RollingMemory

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.game_state import YellowLegacyGameState


class TextHandlerState(BaseState):
    """The state used in the text handler graph workflow."""

    iteration: int | None = None
    rolling_memory: RollingMemory | None = None
    long_term_memory: LongTermMemory | None = None
    goals: Goals | None = None
    handler: TextHandler | None = None

    def to_prompt_string(self, game_state: YellowLegacyGameState) -> str:
        """Get a string representation of the agent and game state to be used in prompts."""
        return "\n\n".join(
            (
                str(self.rolling_memory),
                str(self.long_term_memory),
                str(self.goals),
                game_state.player_info,
            ),
        )


class TextHandlerStore(BaseStore[TextHandlerState]):
    """Concrete store for the text handler state."""

    async def set_state_from_parent(self, parent_state: AgentState) -> None:
        """Set the state from the parent state. Meant to be called at subflow initialization."""
        await self.set_state(
            {
                "iteration": parent_state.iteration,
                "rolling_memory": parent_state.rolling_memory,
                "long_term_memory": parent_state.long_term_memory,
                "goals": parent_state.goals,
            },
        )

    async def set_rolling_memory(self, rolling_memory: RollingMemory) -> None:
        """Set the rolling memory."""
        await self.set_state({"rolling_memory": rolling_memory})

    async def set_handler(self, handler: TextHandler | None) -> None:
        """Set the handler."""
        await self.set_state({"handler": handler})
