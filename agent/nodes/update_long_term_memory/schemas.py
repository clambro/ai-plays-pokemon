"""Data models for update long term memory in the top-level agent graph."""

from enum import StrEnum

from pydantic import BaseModel


class UpdateType(StrEnum):
    """The type of update to perform on a long-term memory object."""

    APPEND = "append"
    REWRITE = "rewrite"


class _UpdateLongTermMemoryResponsePiece(BaseModel):
    """A piece of long-term memory to be created."""

    title: str
    update_type: UpdateType
    content: str


class UpdateLongTermMemoryResponse(BaseModel):
    """The response from the update long-term memory prompt."""

    pieces: list[_UpdateLongTermMemoryResponsePiece]
