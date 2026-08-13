"""Shared dependencies for every gameplay agent."""

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from loguru import logger

from memory.rolling_memory.service import finalize_iteration, initialize_memory

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

    async def complete_iteration(self) -> None:
        """Finalize the current block and advance the live iteration state."""
        try:
            rolling_memory = await finalize_iteration(self.state.rolling_memory)
        except Exception as error:  # noqa: BLE001
            logger.opt(exception=error).warning(
                "Rolling-memory finalization failed; continuing with the current iteration."
            )
            return
        self.state.rolling_memory = rolling_memory
        self.state.iteration = rolling_memory.current_block.iteration
