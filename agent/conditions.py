from junjo.condition import Condition

from agent.state import AgentState
from common.enums import AgentStateHandler


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
