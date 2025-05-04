from datetime import datetime

from common.constants import RAW_MEMORY_MAX_SIZE
from pydantic import BaseModel, Field


class RawMemoryPiece(BaseModel):
    """A single piece of information contained in the Agent's raw memory."""

    iteration: int
    timestamp: datetime
    content: str


class RawMemory(BaseModel):
    """The Agent's raw memory."""

    max_size: int = RAW_MEMORY_MAX_SIZE
    _pieces: list[RawMemoryPiece] = []

    def append(self, *pieces: RawMemoryPiece) -> None:
        """Append a piece to the memory."""
        self._pieces.extend(pieces)
        self._pieces = self._pieces[-self.max_size :]
