"""State models for the battle subflow."""

from typing import TYPE_CHECKING

from junjo import BaseState, BaseStore

from memory.goals import Goals
from memory.long_term_memory import LongTermMemory
from memory.rolling_memory import RollingMemory

if TYPE_CHECKING:
    from agent.state import AgentState


class BattleHandlerState(BaseState):
    """The state used in the battle handler graph workflow."""

    iteration: int | None = None
    rolling_memory: RollingMemory | None = None
    long_term_memory: LongTermMemory | None = None
    goals: Goals | None = None


class BattleHandlerStore(BaseStore[BattleHandlerState]):
    """Concrete store for the battle handler state."""

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
