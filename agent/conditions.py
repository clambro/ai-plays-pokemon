from junjo import Condition

from agent.state import AgentState
from common.enums import AgentStateHandler, Tool


class AgentHandlerIs(Condition[AgentState]):
    """A condition that checks if the agent handler equals a value."""

    def __init__(self, handler: AgentStateHandler | None) -> None:
        self.handler = handler

    def evaluate(self, state: AgentState) -> bool:
        """Evaluate the condition."""
        if self.handler is None and state.handler is None:
            return True
        if self.handler is not None and state.handler is not None:
            return self.handler == state.handler
        return False


class ToolIs(Condition[AgentState]):
    """A condition that checks if the tool equals a value."""

    def __init__(self, tool: Tool | None) -> None:
        self.tool = tool

    def evaluate(self, state: AgentState) -> bool:
        """Evaluate the condition."""
        if self.tool is None and state.tool is None:
            return True
        if self.tool is not None and state.tool is not None:
            return self.tool == state.tool
        return False


class ShouldCritique(Condition[AgentState]):
    """A condition that checks if the agent should_critique value matches a value."""

    def __init__(self, should_critique: bool) -> None:
        self.should_critique = should_critique

    def evaluate(self, state: AgentState) -> bool:
        """Evaluate the condition."""
        return state.should_critique == self.should_critique
