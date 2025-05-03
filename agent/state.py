from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from emulator.enums import Button


class AgentState(BaseModel):
    """The state used in the agent graph workflow."""

    iteration: int
    memory_dir: Path
    backup_dir: Path
    button_presses: list[Button]


class AgentStateParams(StrEnum):
    """The parameters for the agent state as strings for use with Burr."""

    iteration = "iteration"
    memory_dir = "memory_dir"
    backup_dir = "backup_dir"
    button_presses = "button_presses"
