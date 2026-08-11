"""Live and serializable state for the gameplay agents."""

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from memory.goals import Goals
from memory.rolling_memory.schemas import RollingMemory

if TYPE_CHECKING:
    from emulator.game_state import GameState


class AgentState(BaseModel):
    """Mutable gameplay-agent state persisted in application backups."""

    folder: Path
    iteration: int = 0
    rolling_memory: RollingMemory = Field(default_factory=RollingMemory, exclude=True)
    goals: Goals = Field(default_factory=Goals)
    emulator_save_state: str | None = None
    total_tokens: int = 0
    total_cost: float = 0.0

    def to_prompt_string(self, game_state: GameState) -> str:
        """Get a string representation of agent and game state for prompts."""
        return "\n\n".join(
            (
                str(self.rolling_memory),
                str(self.goals),
                game_state.player_info,
            ),
        )
