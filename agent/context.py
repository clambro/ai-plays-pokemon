"""Shared dependencies for every gameplay agent."""

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
from overworld_map.service import record_observed_map_boundary, record_warp_usage

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.emulator import Emulator
    from emulator.game_state import GameState
    from emulator.parsers.warp import WarpTransitionMemory


@dataclass(slots=True, kw_only=True)
class AgentContext:
    """Live dependencies shared by all gameplay agents."""

    state: AgentState
    emulator: Emulator
    _control_handoff_requested: bool = field(
        default=False,
        init=False,
        repr=False,
        compare=False,
    )
    _last_observed_game_state: GameState | None = field(
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
        """Record observed connections and flag repeated arrivals."""
        previous_game_state = self._last_observed_game_state
        previous_transition = self._last_observed_warp_transition
        self._last_observed_game_state = game_state
        self._last_observed_warp_transition = game_state.warp_transition
        if previous_game_state is None:
            return

        previous_map_id = previous_game_state.map.id
        transition = game_state.warp_transition
        destination_warp = game_state.warps.get(transition.destination_warp_index)
        ordinary_warp = (
            transition.is_ordinary_warp
            and transition.source_map_id == previous_map_id
            and destination_warp is not None
        )
        map_changed = previous_map_id != game_state.map.id
        if map_changed:
            await record_observed_map_boundary(previous_game_state, game_state)
        same_map_arrival = (
            not map_changed
            and ordinary_warp
            and previous_transition is not None
            and transition != previous_transition
            and destination_warp is not None
            and destination_warp.coords == game_state.player.coords
        )
        if not map_changed and not same_map_arrival:
            return

        observation = ConnectionTraversalObservation(
            iteration=self.state.iteration,
            map_id=game_state.map.id,
            destination=game_state.player.coords,
        )
        warning = _record_connection_traversal(self.state, observation)
        if warning:
            self.state.rolling_memory.add_memory(warning)

        if not ordinary_warp or destination_warp is None:
            return
        await record_warp_usage(
            iteration=self.state.iteration,
            source_map_id=transition.source_map_id,
            source_warp_id=transition.source_warp_index,
            destination_map_id=game_state.map.id,
            destination_warp=destination_warp,
        )

    async def complete_iteration(self, game_state: GameState) -> None:
        """Record the action's resulting state, then finalize and advance its iteration."""
        await self.observe_game_state(game_state)
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
    """Flag repeated arrivals at the same coordinate on the same map."""
    earliest_iteration = observation.iteration - LOOP_DETECTION_WINDOW_ITERATIONS + 1
    recent_observations = [
        previous
        for previous in state.connection_traversals
        if earliest_iteration <= previous.iteration <= observation.iteration
    ]
    state.connection_traversals = [*recent_observations, observation]

    matching_observations = sum(
        previous.map_id == observation.map_id and previous.destination == observation.destination
        for previous in state.connection_traversals
    )
    if matching_observations < LOOP_DETECTION_REPETITION_THRESHOLD:
        return None
    return (
        f"{CONNECTION_LOOP_LABEL} I have repeatedly arrived at the same location after map"
        f" transitions. I should re-evaluate what I'm doing before continuing."
    )
