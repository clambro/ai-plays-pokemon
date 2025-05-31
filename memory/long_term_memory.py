from pydantic import BaseModel, Field

from database.long_term_memory.schemas import LongTermMemoryRead


class LongTermMemory(BaseModel):
    """A long-term memory object."""

    pieces: dict[str, LongTermMemoryRead] = Field(default_factory=dict)

    def __str__(self) -> str:
        """Get a string representation of the long-term memory."""
        if not self.pieces:
            return ""
        out = (
            "This is your long-term memory. It is a collection of memories that you have created"
            " as you have played the game. The memories shown here do not constitute your entire"
            " long-term memory. They were determined to be relevant to your current situation."
        )
        for title, memory in self.pieces.items():
            out += f"\n<memory>\n{title}\n{memory.content}\n</memory>"
        return out
