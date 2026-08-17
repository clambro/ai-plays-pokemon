"""Shared dependencies for every gameplay agent."""

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from loguru import logger

from memory.rolling_memory.service import finalize_iteration, initialize_memory
from overworld_map.service import record_warp_usage

if TYPE_CHECKING:
    from agent.state import AgentState
    from common.enums import MapId
    from emulator.emulator import Emulator
    from emulator.game_state import GameState


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
    _control_handoff_requested: bool = field(
        default=False,
        init=False,
        repr=False,
        compare=False,
    )
    _last_observed_map_id: MapId | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
    _last_observed_iteration: int | None = field(
        default=None,
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
        self._control_handoff_requested = False
        rolling_memory = await initialize_memory(self.state.rolling_memory.current_block)
        self.state.rolling_memory = rolling_memory
        self.state.iteration = rolling_memory.current_block.iteration

    def request_control_handoff(self) -> None:
        """Request a normal return to the gameplay dispatcher after tool execution."""
        self._control_handoff_requested = True

    def consume_control_handoff(self) -> bool:
        """Consume and clear a pending request to return to the gameplay dispatcher."""
        requested = self._control_handoff_requested
        self._control_handoff_requested = False
        return requested

    async def observe_game_state(self, game_state: GameState) -> None:
        """Persist ordinary warp usage identified between dispatcher states."""
        previous_map_id = self._last_observed_map_id
        previous_iteration = self._last_observed_iteration
        self._last_observed_map_id = game_state.map.id
        self._last_observed_iteration = self.state.iteration
        if (
            previous_map_id is None
            or previous_iteration is None
            or previous_map_id == game_state.map.id
        ):
            return

        transition = game_state.warp_transition
        if (
            not transition.is_ordinary_warp
            or transition.source_map_id != previous_map_id
            or transition.destination_warp_index not in game_state.warps
        ):
            return

        await record_warp_usage(
            iteration=previous_iteration,
            source_map_id=transition.source_map_id,
            source_warp_index=transition.source_warp_index,
            destination_map_id=game_state.map.id,
            destination_warp_index=transition.destination_warp_index,
        )

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
