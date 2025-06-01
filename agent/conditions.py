from junjo import Condition

from agent.state import AgentState
from common.enums import AgentStateHandler


class AgentHandlerIs(Condition[AgentState]):
    """A condition that checks if the agent handler equals a value."""

    def __init__(self, handler: AgentStateHandler | None) -> None:
        self.handler = handler

    def __str__(self) -> str:
        """Return the string representation of the condition."""
        return f"AgentHandlerIs({self.handler})"

    def evaluate(self, state: AgentState) -> bool:
        """Evaluate the condition."""
        if self.handler is None and state.handler is None:
            return True
        if self.handler is not None and state.handler is not None:
            return self.handler == state.handler
        return False


class ShouldRetrieveMemory(Condition[AgentState]):
    """A condition that checks if the agent should retrieve memory."""

    def __init__(self, value: bool) -> None:
        self.value = value

    def __str__(self) -> str:
        """Return the string representation of the condition."""
        return f"ShouldRetrieveMemory({self.value})"

    def evaluate(self, state: AgentState) -> bool:
        """Evaluate the condition."""
        return state.should_retrieve_memory == self.value
