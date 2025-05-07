from enum import StrEnum


class StateHandler(StrEnum):
    """An enum for the different state handlers."""

    OVERWORLD = "overworld"
    BATTLE = "battle"
    TEXT = "text"
