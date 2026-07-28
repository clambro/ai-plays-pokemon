"""Data models for create long term memory in the top-level agent graph."""

from pydantic import BaseModel


class _CreateLongTermMemoryResponsePiece(BaseModel):
    """A piece of long-term memory to be created."""

    title: str
    content: str


class CreateLongTermMemoryResponse(BaseModel):
    """The response from the create long-term memory prompt."""

    pieces: list[_CreateLongTermMemoryResponsePiece]
