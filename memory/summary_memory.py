from loguru import logger
from pydantic import BaseModel, Field

from common.constants import SUMMARY_MEMORY_MAX_SIZE


class SummaryMemoryPiece(BaseModel):
    """A single piece of information contained in the Agent's summary memory."""

    iteration: int
    content: str
    importance: int = Field(ge=1, le=5)

    def __str__(self) -> str:
        """Get a string representation of the memory piece."""
        return f"[{self.iteration}] (Importance: {self.importance}) {self.content}"

    def get_decay_value(self, current_iteration: int) -> float:
        """Get the decay value of the memory piece. Higher values are more likely to decay."""
        return (current_iteration - self.iteration) * (6 - self.importance)


class SummaryMemory(BaseModel):
    """The Agent's summary memory."""

    pieces: list[SummaryMemoryPiece] = Field(default_factory=list)

    def __str__(self) -> str:
        """Get a string representation of the memory."""
        if not self.pieces:
            return ""
        latest_iteration = max(piece.iteration for piece in self.pieces)
        out = (
            f"Here is a summarized representation of your past raw thoughts which, in addition to"
            f" aggregating the information you have learned so far, extends beyond the limits of"
            f" your basic raw memory. Higher iteration numbers (the bracketed numbers) are more"
            f" recent, but keep in mind that the iteration number represents the moment that the"
            f" thought was summarized, not necessarily the moment that it occurred. The latest"
            f" iteration present here is {latest_iteration}. The importance rating is an estimate"
            f" of how important the information was to you at the time of the thought, on a scale"
            f" from 1 to 5, where 5 is the most important."
        )
        out += "\n<summary_memory>\n"
        out += "\n".join([str(piece) for piece in self.pieces])
        out += "\n</summary_memory>"
        return out

    def add_memories(self, iteration: int, *pieces: SummaryMemoryPiece) -> None:
        """Append pieces to the memory, dropping the most decayed pieces if necessary."""
        self.pieces.extend(pieces)
        self.pieces = sorted(self.pieces, key=lambda x: x.get_decay_value(iteration))
        self.pieces = self.pieces[:SUMMARY_MEMORY_MAX_SIZE]
        self.pieces = sorted(self.pieces, key=lambda x: x.iteration)
        for piece in pieces:
            logger.info(f"[{piece.iteration}] New summary memory: {piece.content}")
