from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class AgentState(BaseModel):
    """The state used in the agent graph workflow."""

    iteration: int
    memory_dir: Path
    backup_dir: Path


class AgentStateParams(StrEnum):
    """The parameters for the agent state as strings for use with Burr."""

    iteration = "iteration"
    memory_dir = "memory_dir"
    backup_dir = "backup_dir"
