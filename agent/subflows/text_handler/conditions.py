from junjo import Condition

from agent.subflows.text_handler.enums import TextHandler
from agent.subflows.text_handler.state import TextHandlerState


class HandlerIs(Condition[TextHandlerState]):
    """A condition that checks if the state handler is the given handler."""

    def __init__(self, value: TextHandler | None) -> None:
        self.value = value

    def __str__(self) -> str:
        """Return the string representation of the condition."""
        return f"HandlerIs({self.value})"

    def evaluate(self, state: TextHandlerState) -> bool:
        """Evaluate the condition."""
        if state.handler is None and self.value is None:
            return True
        return state.handler == self.value
