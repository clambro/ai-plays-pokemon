from datetime import datetime

from common.constants import RAW_MEMORY_MAX_SIZE
from pydantic import BaseModel


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
    _pieces: list[RawMemoryPiece] = []

    def __str__(self) -> str:
        """Get a string representation of the memory."""
        if not self._pieces:
            return ""
        out = "Here are the most recent unedited thoughts you have had:\n<raw_memory>\n"
        out += "\n".join([str(piece) for piece in reversed(self._pieces)])
        out += "\n</raw_memory>"
        return out

    def append(self, *pieces: RawMemoryPiece) -> None:
        """Append a piece to the memory."""
        self._pieces.extend(pieces)
        self._pieces = self._pieces[-self.max_size :]
