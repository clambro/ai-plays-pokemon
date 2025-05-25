from pydantic import BaseModel, Field


class _CreateLongTermMemoryResponsePiece(BaseModel):
    """A piece of long-term memory to be created."""

    title: str
    content: str
    importance: int = Field(ge=1, le=3)


class CreateLongTermMemoryResponse(BaseModel):
    """The response from the create long-term memory prompt."""

    pieces: list[_CreateLongTermMemoryResponsePiece]
