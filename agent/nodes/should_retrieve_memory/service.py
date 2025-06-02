from agent.enums import AgentStateHandler
from common.constants import ITERATIONS_PER_LONG_TERM_MEMORY_RETRIEVAL
from memory.long_term_memory import LongTermMemory


class ShouldRetrieveMemoryService:
    """Service for checking if the agent should retrieve memory."""

    def __init__(
        self,
        iteration: int,
        handler: AgentStateHandler,
        previous_handler: AgentStateHandler | None,
        long_term_memory: LongTermMemory,
    ) -> None:
        self.iteration = iteration
        self.handler = handler
        self.previous_handler = previous_handler
        self.long_term_memory = long_term_memory

    async def should_retrieve_memory(self) -> bool:
        """Determine if the agent should retrieve memory."""
        return (
            self.iteration % ITERATIONS_PER_LONG_TERM_MEMORY_RETRIEVAL == 0
            or self.handler != self.previous_handler
            or not self.long_term_memory.pieces
        )
