"""Shared dependencies for every gameplay agent."""

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from memory.long_term_memory import LongTermMemory
from memory.rolling_memory.service import initialize_memory

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.emulator import Emulator


@dataclass(slots=True, kw_only=True)
class AgentContext:
    """Live dependencies shared by all gameplay agents."""

    state: AgentState
    emulator: Emulator
    _llm_usage_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock,
        init=False,
        repr=False,
        compare=False,
    )

    async def add_llm_usage(self, tokens: int, cost: float) -> None:
        """Add one LLM response's usage to the shared state."""
        async with self._llm_usage_lock:
            self.state.total_tokens += tokens
            self.state.total_cost += cost

    async def begin_iteration(self) -> None:
        """Prepare memory for one top-level handler activation."""
        rolling_memory = await initialize_memory(self.state.rolling_memory.current_block)
        self.state.rolling_memory = rolling_memory
        self.state.iteration = rolling_memory.current_block.iteration
        self.state.long_term_memory = LongTermMemory()
