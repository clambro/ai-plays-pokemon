"""State models for the top-level agent graph."""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from junjo import BaseState, BaseStore
from pydantic import Field, field_serializer

from agent.enums import AgentStateHandler
from memory.goals import Goals
from memory.long_term_memory import LongTermMemory
from memory.rolling_memory import CurrentMemoryBlock, RollingMemory

if TYPE_CHECKING:
    from emulator.game_state import YellowLegacyGameState


class AgentState(BaseState):
    """The state used in the agent graph workflow."""

    folder: Path
    iteration: int = 0
    rolling_memory: RollingMemory = Field(default_factory=RollingMemory)
    long_term_memory: LongTermMemory = Field(default_factory=LongTermMemory)
    goals: Goals = Field(default_factory=Goals)
    handler: AgentStateHandler | None = None
    emulator_save_state: str | None = None
    total_tokens: int = 0
    total_cost: float = 0.0

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

    @field_serializer("rolling_memory")
    def serialize_rolling_memory(
        self,
        rolling_memory: RollingMemory,
    ) -> dict[str, CurrentMemoryBlock]:
        """Serialize only the current block; database views are restored from SQLite."""
        return {"current_block": rolling_memory.current_block}


class AgentStore(BaseStore[AgentState]):
    """Concrete store for the agent state."""

    def __init__(self, initial_state: AgentState) -> None:
        """Initialize the store."""
        super().__init__(initial_state)
        self._llm_usage_lock = asyncio.Lock()

    async def set_iteration(self, iteration: int) -> None:
        """Set the iteration."""
        await self.set_state({"iteration": iteration})

    async def set_rolling_memory(self, rolling_memory: RollingMemory) -> None:
        """Set the rolling memory."""
        await self.set_state({"rolling_memory": rolling_memory})

    async def set_long_term_memory(self, long_term_memory: LongTermMemory) -> None:
        """Set the long-term memory."""
        await self.set_state({"long_term_memory": long_term_memory})

    async def set_goals(self, goals: Goals) -> None:
        """Set the goals."""
        await self.set_state({"goals": goals})

    async def set_handler(self, handler: AgentStateHandler) -> None:
        """Set the handler."""
        await self.set_state({"handler": handler})

    async def add_llm_usage(self, tokens: int, cost: float) -> None:
        """Add one LLM call's usage to the run totals.

        Args:
            tokens: Tokens consumed by the call.
            cost: Cost incurred by the call.
        """
        async with self._llm_usage_lock:
            state = await self.get_state()
            await self.set_state(
                {
                    "total_tokens": state.total_tokens + tokens,
                    "total_cost": state.total_cost + cost,
                },
            )
