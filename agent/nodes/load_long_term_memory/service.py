from database.long_term_memory.schemas import LongTermMemoryRead
from raw_memory.schemas import RawMemory
from summary_memory.schemas import SummaryMemory


class LoadLongTermMemoryService:
    """Service for loading the long-term memory."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        summary_memory: SummaryMemory,
        last_long_term_memory: list[LongTermMemoryRead],
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.summary_memory = summary_memory
        self.last_long_term_memory = last_long_term_memory

    async def load_long_term_memory(self) -> list[LongTermMemoryRead]:
        """Load the long-term memory."""
        return self.last_long_term_memory
