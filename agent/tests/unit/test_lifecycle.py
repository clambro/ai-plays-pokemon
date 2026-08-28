"""Behavior tests for shared agent context."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import context as context_module
from agent.context import AgentContext
from agent.state import AgentState
from common.enums import MapId
from common.schemas import Coords
from database.rolling_memory.schemas import RawMemoryBlockRead
from emulator.parsers.warp import WarpTransitionMemory
from memory.rolling_memory import service as rolling_memory_service
from memory.rolling_memory.schemas import CurrentMemoryBlock, RollingMemory

if TYPE_CHECKING:
    from pathlib import Path


def _transition_state(
    map_id: MapId,
    transition: WarpTransitionMemory,
    warp_indices: frozenset[int] = frozenset(),
) -> MagicMock:
    """Build the game-state behavior needed by transition tracking."""
    game_state = MagicMock()
    game_state.map.id = map_id
    game_state.warps = {index: MagicMock() for index in warp_indices}
    game_state.warp_transition = transition
    return game_state


@pytest.mark.unit
async def test_begin_iteration_prepares_handler_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Initialize rolling memory once at the start of a handler activation."""
    iteration = 6
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=iteration,
            rolling_memory=RollingMemory(current_block=CurrentMemoryBlock(iteration=iteration)),
        ),
        emulator=MagicMock(),
    )
    prepared_memory = RollingMemory(
        current_block=CurrentMemoryBlock(iteration=iteration),
    )
    original_block = context.state.rolling_memory.current_block
    initialize_memory = AsyncMock(return_value=prepared_memory)
    monkeypatch.setattr(context_module, "initialize_memory", initialize_memory)

    await context.begin_iteration()

    initialize_memory.assert_awaited_once_with(original_block)
    assert context.state.iteration == iteration


@pytest.mark.unit
async def test_complete_iteration_advances_after_maintenance_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Keep live memory aligned after persistence succeeds but maintenance fails."""
    iteration = 6
    content = "I tried to move north, but a wall blocked the way."
    context = AgentContext(
        state=AgentState(
            folder=tmp_path,
            iteration=iteration,
            rolling_memory=RollingMemory(
                current_block=CurrentMemoryBlock(iteration=iteration, content=content),
            ),
        ),
        emulator=MagicMock(),
    )
    monkeypatch.setattr(
        rolling_memory_service,
        "finalize_raw_memory_block",
        AsyncMock(return_value=RawMemoryBlockRead(iteration=iteration, content=content)),
    )
    monkeypatch.setattr(
        rolling_memory_service,
        "compact_memory",
        AsyncMock(side_effect=RuntimeError("compaction unavailable")),
    )

    await context.complete_iteration()

    assert context.state.iteration == iteration + 1
    assert context.state.rolling_memory.current_block == CurrentMemoryBlock(
        iteration=iteration + 1,
    )
    assert context.state.rolling_memory.loaded_raw_blocks[-1].iteration == iteration
    assert context.state.rolling_memory.loaded_raw_blocks[-1].content == content


@pytest.mark.unit
async def test_game_state_observation_records_rom_identified_ordinary_warp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report both endpoints after the ROM identity matches both maps."""
    iteration = 42
    source_warp_index = 2
    destination_warp_index = 0
    transition = WarpTransitionMemory(
        source_map_id=MapId.ROUTE_3,
        source_warp_index=source_warp_index,
        destination_warp_index=destination_warp_index,
    )
    previous_state = _transition_state(
        MapId.ROUTE_3,
        transition,
    )
    current_state = _transition_state(
        MapId.MT_MOON_1F,
        transition,
        frozenset({destination_warp_index}),
    )
    destination_warp = current_state.warps[destination_warp_index]
    context = AgentContext(
        state=AgentState(folder=tmp_path, iteration=iteration),
        emulator=MagicMock(),
    )
    record_warp_usage = AsyncMock()
    monkeypatch.setattr(context_module, "record_warp_usage", record_warp_usage)

    await context.observe_game_state(previous_state)
    context.state.iteration += 1
    await context.observe_game_state(current_state)

    record_warp_usage.assert_awaited_once_with(
        iteration=iteration,
        source_map_id=MapId.ROUTE_3,
        source_warp_id=source_warp_index,
        destination_map_id=MapId.MT_MOON_1F,
        destination_warp=destination_warp,
    )


@pytest.mark.unit
async def test_game_state_observation_warns_after_rapid_connection_backtracking(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Flag repeated travel through both directions of one ordinary connection."""
    route_warp_index = 2
    cave_warp_index = 0
    route_to_cave = WarpTransitionMemory(
        source_map_id=MapId.ROUTE_3,
        source_warp_index=route_warp_index,
        destination_warp_index=cave_warp_index,
    )
    cave_to_route = WarpTransitionMemory(
        source_map_id=MapId.MT_MOON_1F,
        source_warp_index=cave_warp_index,
        destination_warp_index=route_warp_index,
    )
    route_state = _transition_state(
        MapId.ROUTE_3,
        cave_to_route,
        frozenset({route_warp_index}),
    )
    cave_state = _transition_state(
        MapId.MT_MOON_1F,
        route_to_cave,
        frozenset({cave_warp_index}),
    )
    context = AgentContext(
        state=AgentState(folder=tmp_path, iteration=1),
        emulator=MagicMock(),
    )
    monkeypatch.setattr(context_module, "record_warp_usage", AsyncMock())

    await context.observe_game_state(route_state)
    for iteration, game_state in enumerate(
        (cave_state, route_state, cave_state),
        start=2,
    ):
        context.state.iteration = iteration
        await context.observe_game_state(game_state)

    warning = context.state.rolling_memory.current_block.content
    assert warning
    assert context.state.public_log.entries == []

    context.state.iteration += 1
    await context.observe_game_state(route_state)

    assert context.state.rolling_memory.current_block.content == warning


@pytest.mark.unit
async def test_game_state_observation_records_same_map_warp_arrival(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Record a new ROM warp identity that arrives elsewhere on the same map."""
    iteration = 42
    destination_warp_index = 22
    previous_transition = WarpTransitionMemory(
        source_map_id=MapId.SAFFRON_GYM,
        source_warp_index=4,
        destination_warp_index=15,
    )
    current_transition = WarpTransitionMemory(
        source_map_id=MapId.SAFFRON_GYM,
        source_warp_index=2,
        destination_warp_index=destination_warp_index,
    )
    previous_state = _transition_state(MapId.SAFFRON_GYM, previous_transition)
    current_state = _transition_state(
        MapId.SAFFRON_GYM,
        current_transition,
        frozenset({destination_warp_index}),
    )
    destination_coords = Coords(row=3, col=1)
    destination_warp = current_state.warps[destination_warp_index]
    destination_warp.coords = destination_coords
    current_state.player.coords = destination_coords
    context = AgentContext(
        state=AgentState(folder=tmp_path, iteration=iteration),
        emulator=MagicMock(),
    )
    record_warp_usage = AsyncMock()
    monkeypatch.setattr(context_module, "record_warp_usage", record_warp_usage)

    await context.observe_game_state(previous_state)
    context.state.iteration += 1
    await context.observe_game_state(current_state)

    record_warp_usage.assert_awaited_once_with(
        iteration=iteration,
        source_map_id=MapId.SAFFRON_GYM,
        source_warp_id=2,
        destination_map_id=MapId.SAFFRON_GYM,
        destination_warp=destination_warp,
    )
    record_warp_usage.reset_mock()

    context.state.iteration += 1
    await context.observe_game_state(current_state)

    record_warp_usage.assert_not_awaited()


@pytest.mark.unit
async def test_game_state_observation_rejects_stale_warp_identity_on_boundary_crossing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Do not turn persistent ordinary-warp registers into a boundary arrival."""
    transition = WarpTransitionMemory(
        source_map_id=MapId.MT_MOON_1F,
        source_warp_index=2,
        destination_warp_index=0,
    )
    previous_state = _transition_state(MapId.ROUTE_3, transition)
    current_state = _transition_state(
        MapId.ROUTE_4,
        transition,
        frozenset({0}),
    )
    context = AgentContext(state=AgentState(folder=tmp_path), emulator=MagicMock())
    record_warp_usage = AsyncMock()
    monkeypatch.setattr(context_module, "record_warp_usage", record_warp_usage)

    await context.observe_game_state(previous_state)
    await context.observe_game_state(current_state)

    record_warp_usage.assert_not_awaited()


@pytest.mark.unit
async def test_game_state_observation_rejects_special_travel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Do not report usage when the ROM excludes normal warps."""
    context = AgentContext(state=AgentState(folder=tmp_path), emulator=MagicMock())
    ordinary_transition = WarpTransitionMemory(
        source_map_id=MapId.SEAFOAM_ISLANDS_B3F,
        source_warp_index=5,
        destination_warp_index=0,
    )
    special_transition = WarpTransitionMemory(
        source_map_id=MapId.SEAFOAM_ISLANDS_B3F,
        source_warp_index=5,
        destination_warp_index=0xFF,
    )
    previous_state = _transition_state(MapId.SEAFOAM_ISLANDS_B4F, ordinary_transition)
    current_state = _transition_state(MapId.FUCHSIA_CITY, special_transition)
    record_warp_usage = AsyncMock()
    monkeypatch.setattr(context_module, "record_warp_usage", record_warp_usage)

    await context.observe_game_state(previous_state)
    await context.observe_game_state(current_state)

    record_warp_usage.assert_not_awaited()
