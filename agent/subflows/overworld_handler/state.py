"""State models for the overworld subflow."""

from typing import TYPE_CHECKING

from junjo import BaseState, BaseStore

from memory.goals import Goals
from memory.long_term_memory import LongTermMemory
from memory.rolling_memory import RollingMemory
from overworld_map.schemas import OverworldMap

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.game_state import YellowLegacyGameState


class OverworldHandlerState(BaseState):
    """The state used in the overworld handler graph workflow."""

    iteration: int | None = None
    rolling_memory: RollingMemory | None = None
    long_term_memory: LongTermMemory | None = None
    goals: Goals | None = None
    current_map: OverworldMap | None = None

    def to_prompt_string(self, game_state: YellowLegacyGameState) -> str:
        """Get a string representation of the agent and game state to be used in prompts."""
        if self.current_map is None:
            raise ValueError("Current map is not set")
        return "\n\n".join(
            (
                str(self.rolling_memory),
                str(self.long_term_memory),
                str(self.goals),
                self.current_map.to_string(game_state),
                game_state.player_info,
            ),
        )


class OverworldHandlerStore(BaseStore[OverworldHandlerState]):
    """Concrete store for the overworld handler state."""

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

    async def set_current_map(self, current_map: OverworldMap) -> None:
        """Set the current map."""
        await self.set_state({"current_map": current_map})
