"""Routing conditions for the overworld subflow."""

from typing import TYPE_CHECKING

from junjo import Condition

from agent.subflows.overworld_handler.state import OverworldHandlerState

if TYPE_CHECKING:
    from agent.subflows.overworld_handler.enums import OverworldTool


class ToolIs(Condition[OverworldHandlerState]):
    """A condition that checks if the tool equals a value."""

    def __init__(self, tool: OverworldTool) -> None:
        """Initialize the condition with the expected tool."""
        self.tool = tool

    def __str__(self) -> str:
        """Return the string representation of the condition."""
        return f"ToolIs({self.tool})"

    def evaluate(self, state: OverworldHandlerState) -> bool:
        """Evaluate the condition."""
        return self.tool == state.tool
