from loguru import logger
from pydantic import BaseModel, Field

from common.constants import RAW_MEMORY_MAX_SIZE


class RawMemoryPiece(BaseModel):
    """A single piece of information contained in the Agent's raw memory."""

    iteration: int
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
            f"Here are the raw thoughts you have had prior to this point. The bracketed number is"
            f" the incremented iteration number at which you had the thought. Higher numbers are"
            f" more recent. The latest iteration is {self.pieces[-1].iteration}. Only the most"
            f" recent {self.max_size} thoughts are displayed in this section. To give you an"
            f" indication of the passage of time, each iteration takes roughly three seconds."
        )
        out += "\n<raw_memory>\n"
        out += "\n".join([str(piece) for piece in self.pieces])
        out += "\n</raw_memory>"
        return out

    def append(self, *pieces: RawMemoryPiece) -> None:
        """Append a piece to the memory."""
        self.pieces.extend(pieces)
        self.pieces = self.pieces[-self.max_size :]
        for piece in pieces:
            logger.info(f"[{piece.iteration}] New thought: {piece.content}")
