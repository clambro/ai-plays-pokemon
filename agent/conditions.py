from typing import Any
from burr.core import Condition, State

from agent.state import AgentState


def field_equals_value(field: str, value: Any) -> Condition:
    """A condition that checks if a field equals a value."""

    def resolver(state: State) -> bool:  # Burr forces the generic State type here.
        validated_state = AgentState.model_validate(state)
        return getattr(validated_state, field) == value

    return Condition(keys=[field], resolver=resolver)
