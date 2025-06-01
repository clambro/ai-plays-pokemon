from junjo import Condition

from agent.subflows.text_handler.state import TextHandlerState


class NeedsGenericHandling(Condition[TextHandlerState]):
    """A condition that checks if the agent needs generic handling."""

    def __init__(self, needs_generic_handling: bool) -> None:
        self.needs_generic_handling = needs_generic_handling

    def __str__(self) -> str:
        """Return the string representation of the condition."""
        return f"NeedsGenericHandling({self.needs_generic_handling})"

    def evaluate(self, state: TextHandlerState) -> bool:
        """Evaluate the condition."""
        return state.needs_generic_handling == self.needs_generic_handling
