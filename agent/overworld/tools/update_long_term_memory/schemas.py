"""Models for long-term-memory updates."""

from enum import StrEnum


class UpdateType(StrEnum):
    """The operation to apply to an existing memory document."""

    APPEND = "append"
    REWRITE = "rewrite"
