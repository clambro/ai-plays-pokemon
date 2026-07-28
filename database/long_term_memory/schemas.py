"""Data-transfer models for long term memory."""

from pydantic import BaseModel, ConfigDict


class LongTermMemoryCreate(BaseModel):
    """Create schema for long-term memory."""

    title: str
    content: str
    iteration: int


class LongTermMemoryRead(BaseModel):
    """Read schema for long-term memory."""

    title: str
    content: str

    model_config = ConfigDict(from_attributes=True)


class LongTermMemoryUpdate(BaseModel):
    """Update schema for long-term memory."""

    title: str
    content: str
    iteration: int
