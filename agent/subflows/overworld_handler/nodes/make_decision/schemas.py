from pydantic import BaseModel

from agent.schemas import NavigationArgs
from agent.subflows.overworld_handler.enums import OverworldTool
from memory.raw_memory import RawMemory


class MakeDecisionResponse(BaseModel):
    """The response from the overworld decision maker prompt."""

    thoughts: str
    tool: OverworldTool


class Decision(BaseModel):
    """The decision from the overworld decision maker prompt."""

    raw_memory: RawMemory
    tool: OverworldTool | None
    navigation_args: NavigationArgs | None
