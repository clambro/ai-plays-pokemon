from datetime import datetime

from common.constants import RAW_MEMORY_MAX_SIZE
from pydantic import BaseModel, Field


class RawMemoryPiece(BaseModel):
    """A single piece of information contained in the Agent's raw memory."""

    iteration: int
    timestamp: datetime
    content: str

    def __str__(self) -> str:
        """Get a string representation of the memory piece."""
        return f"[{self.iteration}]: {self.content}"


class RawMemory(BaseModel):
    """The Agent's raw memory."""

    max_size: int = RAW_MEMORY_MAX_SIZE
    pieces: list[RawMemoryPiece] = Field(default_factory=list)

    def __str__(self) -> str:
        """Get a string representation of the memory."""
        if not self.pieces:
            return ""
        out = (
            "Here are the most recent unedited thoughts you have had. The bracketed number is the"
            " incremented iteration number at which you had the thought. Higher numbers are more"
            " recent.\n<raw_memory>\n"
        )
        out += "\n".join([str(piece) for piece in reversed(self.pieces)])
        out += "\n</raw_memory>"
        return out

    def append(self, *pieces: RawMemoryPiece) -> None:
        """Append a piece to the memory."""
        self.pieces.extend(pieces)
        self.pieces = self.pieces[-self.max_size :]
