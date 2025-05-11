from enum import StrEnum


class AgentStateHandler(StrEnum):
    """An enum for the different state handlers."""

    OVERWORLD = "overworld"
    BATTLE = "battle"
    TEXT = "text"


class Tool(StrEnum):
    """An enum for the different tools."""

    NAVIGATE = "navigate"
