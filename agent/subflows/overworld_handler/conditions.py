from junjo import Condition

from agent.subflows.overworld_handler.enums import OverworldTool
from agent.subflows.overworld_handler.state import OverworldHandlerState


class ToolIs(Condition[OverworldHandlerState]):
    """A condition that checks if the tool equals a value."""

    def __init__(self, tool: OverworldTool | None) -> None:
        self.tool = tool

    def __str__(self) -> str:
        """Return the string representation of the condition."""
        return f"ToolIs({self.tool})"

    def evaluate(self, state: OverworldHandlerState) -> bool:
        """Evaluate the condition."""
        if self.tool is None and state.tool is None:
            return True
        if self.tool is not None and state.tool is not None:
            return self.tool == state.tool
        return False


class ShouldCritique(Condition[OverworldHandlerState]):
    """A condition that checks if the agent should_critique value matches a value."""

    def __init__(self, should_critique: bool) -> None:
        self.should_critique = should_critique

    def __str__(self) -> str:
        """Return the string representation of the condition."""
        return f"ShouldCritique({self.should_critique})"

    def evaluate(self, state: OverworldHandlerState) -> bool:
        """Evaluate the condition."""
        return state.should_critique == self.should_critique
