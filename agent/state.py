"""Live and serializable state for the gameplay agents."""

from pathlib import Path

from pydantic import BaseModel, Field

from agent.schemas import ScriptedDisplacementObservation
from memory.goals import Goals
from memory.rolling_memory.schemas import RollingMemory


class AgentState(BaseModel):
    """Mutable gameplay-agent state persisted in application backups."""

    folder: Path
    iteration: int = 0
    rolling_memory: RollingMemory = Field(default_factory=RollingMemory, exclude=True)
    goals: Goals = Field(default_factory=Goals)
    scripted_displacements: list[ScriptedDisplacementObservation] = Field(default_factory=list)
    emulator_save_state: str | None = None
    total_tokens: int = 0
    total_cost: float = 0.0
