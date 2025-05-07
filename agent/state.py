from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from common.enums import StateHandler
from common.goals import Goals
from emulator.enums import Button
from overworld_map.schemas import OverworldMap
from raw_memory.schemas import RawMemory


class AgentState(BaseModel):
    """The state used in the agent graph workflow."""

    folder: Path
    iteration: int = 0
    buttons_pressed: list[Button] = Field(default_factory=list)
    raw_memory: RawMemory = Field(default_factory=RawMemory)
    handler: StateHandler | None = None
    current_map: OverworldMap | None = None
    goals: Goals = Field(default_factory=Goals)


class AgentStateParams(StrEnum):
    """The parameters for the agent state as strings for use with Burr."""

    folder = "folder"
    iteration = "iteration"
    buttons_pressed = "buttons_pressed"
    raw_memory = "raw_memory"
    handler = "handler"
    current_map = "current_map"
