"""Data-transfer models for rolling memory."""

from pydantic import BaseModel, ConfigDict


class RawMemoryBlockCreate(BaseModel):
    """Create schema for a finalized raw-memory block."""

    iteration: int
    content: str


class RawMemoryBlockRead(BaseModel):
    """Read schema for a finalized raw-memory block."""

    iteration: int
    content: str

    model_config = ConfigDict(from_attributes=True)


class MemorySummaryCreate(BaseModel):
    """Create schema for a derived memory summary."""

    start_iteration: int
    end_iteration: int
    level: int
    content: str


class MemorySummaryRead(BaseModel):
    """Read schema for a derived memory summary."""

    start_iteration: int
    end_iteration: int
    level: int
    content: str

    model_config = ConfigDict(from_attributes=True)
