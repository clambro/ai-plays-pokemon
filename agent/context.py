"""Shared dependencies for every gameplay agent."""

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from loguru import logger

from agent.schemas import ConnectionTraversalObservation
from common.constants import (
    CONNECTION_LOOP_LABEL,
    LOOP_DETECTION_REPETITION_THRESHOLD,
    LOOP_DETECTION_WINDOW_ITERATIONS,
)
from memory.rolling_memory.service import finalize_iteration, initialize_memory
from overworld_map.service import record_warp_usage

if TYPE_CHECKING:
    from agent.state import AgentState
    from common.enums import MapId
    from emulator.emulator import Emulator
    from emulator.game_state import GameState
    from emulator.parsers.warp import WarpTransitionMemory


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
    _last_observed_warp_transition: WarpTransitionMemory | None = field(
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
        previous_transition = self._last_observed_warp_transition
        self._last_observed_map_id = game_state.map.id
        self._last_observed_iteration = self.state.iteration
        self._last_observed_warp_transition = game_state.warp_transition
        if previous_map_id is None or previous_iteration is None:
            return

        transition = game_state.warp_transition
        destination_warp = game_state.warps.get(transition.destination_warp_index)
        if (
            not transition.is_ordinary_warp
            or transition.source_map_id != previous_map_id
            or destination_warp is None
        ):
            return

        map_changed = previous_map_id != game_state.map.id
        same_map_arrival = (
            not map_changed
            and previous_transition is not None
            and transition != previous_transition
            and destination_warp.coords == game_state.player.coords
        )
        if not map_changed and not same_map_arrival:
            return

        await record_warp_usage(
            iteration=previous_iteration,
            source_map_id=transition.source_map_id,
            source_warp_id=transition.source_warp_index,
            destination_map_id=game_state.map.id,
            destination_warp=destination_warp,
        )
        observation = ConnectionTraversalObservation(
            iteration=previous_iteration,
            source_map_id=transition.source_map_id,
            source_warp_id=transition.source_warp_index,
            destination_map_id=game_state.map.id,
            destination_warp_id=transition.destination_warp_index,
        )
        warning = _record_connection_traversal(self.state, observation)
        if warning:
            self.state.rolling_memory.add_memory(warning)

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


def _record_connection_traversal(
    state: AgentState,
    observation: ConnectionTraversalObservation,
) -> str | None:
    """Record an ordinary warp traversal and flag rapid backtracking."""
    earliest_iteration = observation.iteration - LOOP_DETECTION_WINDOW_ITERATIONS + 1
    recent_observations = [
        previous
        for previous in state.connection_traversals
        if earliest_iteration <= previous.iteration <= observation.iteration
    ]
    state.connection_traversals = [*recent_observations, observation]

    connection = _connection_endpoints(observation)
    matching_observations = [
        previous
        for previous in state.connection_traversals
        if _connection_endpoints(previous) == connection
    ]
    if len(matching_observations) != LOOP_DETECTION_REPETITION_THRESHOLD or all(
        (previous.source_map_id, previous.source_warp_id)
        == (observation.source_map_id, observation.source_warp_id)
        for previous in matching_observations
    ):
        return None
    return (
        f"{CONNECTION_LOOP_LABEL} I have repeatedly crossed the same connection in both"
        " directions without making progress. I should use check_connection to reconstruct the"
        " surrounding connections, determine which side contains the route I need, and then move"
        " away from this connection. If I must cross it once more, I should not immediately reverse"
        " direction again."
    )


def _connection_endpoints(
    observation: ConnectionTraversalObservation,
) -> frozenset[tuple[MapId, int]]:
    """Return a direction-independent identity for a traversed connection."""
    return frozenset(
        {
            (observation.source_map_id, observation.source_warp_id),
            (observation.destination_map_id, observation.destination_warp_id),
        }
    )
