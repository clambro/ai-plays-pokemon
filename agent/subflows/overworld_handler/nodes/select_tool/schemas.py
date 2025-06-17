from pydantic import BaseModel

from agent.subflows.overworld_handler.enums import OverworldTool


class SelectToolResponse(BaseModel):
    """The response from the overworld tool selector prompt."""

    thoughts: str
    tool: OverworldTool
