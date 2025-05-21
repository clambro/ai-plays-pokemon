from pydantic import UUID4, BaseModel, ConfigDict, Field


class LongTermMemoryCreate(BaseModel):
    """Create schema for long-term memory."""

    title: str
    content: str
    importance: int = Field(ge=1, le=5)
    embedding: list[float]
    iteration: int


class LongTermMemoryRead(BaseModel):
    """Read schema for long-term memory."""

    id: UUID4
    title: str
    content: str
    importance: int = Field(ge=1, le=5)
    last_accessed_iteration: int

    model_config = ConfigDict(from_attributes=True)


class LongTermMemoryUpdate(BaseModel):
    """Update schema for long-term memory."""

    id: UUID4
    content: str
    importance: int = Field(ge=1, le=5)
    iteration: int
