from junjo import Condition

from agent.subflows.battle_handler.schemas import BattleToolArgs
from agent.subflows.battle_handler.state import BattleHandlerState


class ToolArgsIs(Condition[BattleHandlerState]):
    """A condition that checks if the state tool args is the given tool args."""

    def __init__(self, value: type[BattleToolArgs] | None) -> None:
        self.value = value

    def __str__(self) -> str:
        """Return the string representation of the condition."""
        name = self.value.__name__ if self.value is not None else "None"
        return f"ToolArgsIs({name})"

    def evaluate(self, state: BattleHandlerState) -> bool:
        """Evaluate the condition."""
        if state.tool_args is None and self.value is None:
            return True
        return isinstance(state.tool_args, self.value) if self.value is not None else False
