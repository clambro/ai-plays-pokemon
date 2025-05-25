from pydantic import BaseModel, Field

from database.long_term_memory.schemas import LongTermMemoryRead


class LongTermMemory(BaseModel):
    """A long-term memory object."""

    pieces: list[LongTermMemoryRead] = Field(default_factory=list)

    def __str__(self) -> str:
        """Get a string representation of the long-term memory."""
        if not self.pieces:
            return "No long-term memories found."

        out = (
            "This is your long-term memory. It is a collection of memories that you have created"
            " as you have played the game. The memories shown here do not constitute your entire"
            " long-term memory. They were determined to be relevant to your current situation."
        )
        for piece in self.pieces:
            out += f"\n<memory>\n{piece.title}\n{piece.content}\n</memory>"
        return out
