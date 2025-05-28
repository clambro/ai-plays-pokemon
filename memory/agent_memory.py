from pydantic import BaseModel, Field

from memory.long_term_memory import LongTermMemory
from memory.raw_memory import RawMemory
from memory.summary_memory import SummaryMemory


class AgentMemory(BaseModel):
    """Facade class for the collection of memory objects that the agent has."""

    raw_memory: RawMemory = Field(default_factory=RawMemory)
    summary_memory: SummaryMemory = Field(default_factory=SummaryMemory)
    long_term_memory: LongTermMemory = Field(default_factory=LongTermMemory)

    def __str__(self) -> str:
        """Get a string representation of the agent memory."""
        return f"{self.raw_memory}\n\n{self.summary_memory}\n\n{self.long_term_memory}"
