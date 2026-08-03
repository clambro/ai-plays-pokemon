"""State models for the top-level agent graph."""

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

    async def set_handler(self, handler: AgentStateHandler) -> None:
        """Set the handler."""
        await self.set_state({"handler": handler})

    async def replace_state(self, state: AgentState) -> None:
        """Copy the shared agent state back into the temporary Junjo store."""
        await self.set_state(
            {field_name: getattr(state, field_name) for field_name in AgentState.model_fields},
        )
