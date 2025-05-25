from enum import StrEnum

from pydantic import BaseModel, Field


class UpdateType(StrEnum):
    """The type of update to perform on a long-term memory object."""

    APPEND = "append"
    REWRITE = "rewrite"


class _UpdateLongTermMemoryResponsePiece(BaseModel):
    """A piece of long-term memory to be created."""

    title: str
    update_type: UpdateType
    content: str
    importance: int = Field(ge=1, le=3)


class UpdateLongTermMemoryResponse(BaseModel):
    """The response from the update long-term memory prompt."""

    pieces: list[_UpdateLongTermMemoryResponsePiece]
