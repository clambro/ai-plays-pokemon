from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from emulator.game_state import YellowLegacyGameState


class AgentState(BaseModel):
    """The state used in the agent graph workflow."""

    iteration: int
    game_state: YellowLegacyGameState
    screenshot: bytes
    memory_dir: Path
    backup_dir: Path


class AgentStateParams(StrEnum):
    """The parameters for the agent state as strings for use with Burr."""

    game_state = "game_state"
    screenshot = "screenshot"
    memory_dir = "memory_dir"
    backup_dir = "backup_dir"
