from pydantic import BaseModel, Field

from database.long_term_memory.schemas import LongTermMemoryRead
from memory.long_term_memory import LongTermMemory
from memory.raw_memory import RawMemory, RawMemoryPiece
from memory.summary_memory import SummaryMemory, SummaryMemoryPiece


class AgentMemory(BaseModel):
    """Facade class for the collection of memory objects that the agent has."""

    raw_memory: RawMemory = Field(default_factory=RawMemory)
    summary_memory: SummaryMemory = Field(default_factory=SummaryMemory)
    long_term_memory: LongTermMemory = Field(default_factory=LongTermMemory)

    def __str__(self) -> str:
        """Get a string representation of the agent memory."""
        return f"{self.raw_memory}\n\n{self.summary_memory}\n\n{self.long_term_memory}"

    @property
    def has_long_term_memory(self) -> bool:
        """Check if the agent has non-empty long-term memory."""
        return bool(self.long_term_memory.pieces)

    @property
    def long_term_memory_map(self) -> dict[str, LongTermMemoryRead]:
        """Get a map of title to long-term memory piece."""
        return self.long_term_memory.pieces

    def append_raw_memory(self, *pieces: RawMemoryPiece) -> None:
        """Append a raw memory piece to the agent memory."""
        self.raw_memory.append(*pieces)

    def append_summary_memory(self, iteration: int, *pieces: SummaryMemoryPiece) -> None:
        """Append a summary memory piece to the agent memory."""
        self.summary_memory.append(iteration, *pieces)

    def replace_long_term_memory(self, new_memories: list[LongTermMemoryRead]) -> None:
        """Replace the long-term memory with a new set of memories."""
        self.long_term_memory.pieces = {memory.title: memory for memory in new_memories}
