"""Enumerations used by the top-level agent graph."""

from enum import StrEnum


class AgentStateHandler(StrEnum):
    """An enum for the different state handlers."""

    OVERWORLD = "overworld"
    BATTLE = "battle"
    TEXT = "text"
