from pydantic import BaseModel

from agent.subflows.overworld_handler.enums import OverworldTool


class MakeDecisionResponse(BaseModel):
    """The response from the overworld decision maker prompt."""

    thoughts: str
    tool: OverworldTool
