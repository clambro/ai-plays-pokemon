from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from emulator.enums import Button
from raw_memory.schemas import RawMemory


class AgentState(BaseModel):
    """The state used in the agent graph workflow."""

    memory_dir: Path
    backup_dir: Path
    iteration: int = 0
    buttons_pressed: list[Button] = Field(default_factory=list)
    raw_memory: RawMemory = Field(default_factory=RawMemory)


class AgentStateParams(StrEnum):
    """The parameters for the agent state as strings for use with Burr."""

    memory_dir = "memory_dir"
    backup_dir = "backup_dir"
    iteration = "iteration"
    buttons_pressed = "buttons_pressed"
    raw_memory = "raw_memory"
