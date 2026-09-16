"""Inspect remembered map arrivals without navigating the player."""

from typing import TYPE_CHECKING

import numpy as np
from loguru import logger

from agent.overworld.connections import group_contiguous_warps, group_map_boundaries
from agent.overworld.navigation import get_accessible_coords, get_exploration_candidates
from agent.overworld.tools.inspect_map.schemas import (
    ConnectionComponent,
    MapArrivalInspection,
    MapInspectionError,
    MapInspectionResult,
    ResolvedConnection,
)
from common.enums import AsciiTile, MapId
from common.schemas import Coords
from database.map_boundary_memory.repository import (
    get_map_boundary_memories_for_map,
    get_map_boundary_memories_to_map,
)
from database.map_memory.repository import get_map_memory, get_visited_maps
from database.warp_memory.repository import get_warp_memories_for_map, get_warp_memories_to_map

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from agent.overworld.tools.inspect_map.schemas import WarpGroups
    from database.map_boundary_memory.schemas import MapBoundaryMemoryRead
    from database.map_memory.schemas import MapMemoryRead
    from database.warp_memory.schemas import WarpMemoryRead


async def inspect_map(
    *,
    map_name: str,
    hm_tiles: list[AsciiTile],
) -> MapInspectionResult | MapInspectionError:
    """Inspect reachable connections and exploration from every known map entrance."""
    try:
        map_id = MapId[map_name]
    except KeyError:
        return MapInspectionError.INVALID_MAP
    if map_id in {MapId.OUTSIDE, MapId.UNKNOWN}:
        return MapInspectionError.UNSUPPORTED_MAP

    try:
        return await _inspect_map(map_id=map_id, hm_tiles=hm_tiles)
    except Exception as error:  # noqa: BLE001
        logger.opt(exception=error).warning(
            "Map inspection failed; continuing without remembered connectivity."
        )
        return MapInspectionError.MEMORY_UNAVAILABLE


async def _inspect_map(
    *,
    map_id: MapId,
    hm_tiles: list[AsciiTile],
) -> MapInspectionResult | MapInspectionError:
    """Keep each entrance's directional reachability independent."""
    known_map_ids = frozenset(await get_visited_maps())
    if map_id not in known_map_ids:
        return MapInspectionError.UNVISITED_MAP
    map_memory = await get_map_memory(map_id)
    if map_memory is None:
        return MapInspectionError.UNVISITED_MAP

    warps = await get_warp_memories_for_map(map_id)
    warp_groups_by_map = {map_id: group_remembered_warps(warps)}
    boundaries = await get_map_boundary_memories_for_map(map_id)
    incoming_boundaries = await get_map_boundary_memories_to_map(map_id)
    incoming_warps = await get_warp_memories_to_map(map_id)
    incoming_warp_ids = {warp.destination_warp_id for warp in incoming_warps}
    entry_coords = {
        *(_coords(warp) for warp in warps if warp.last_used_iteration is not None),
        *(_coords(warp) for warp in warps if warp.warp_id in incoming_warp_ids),
        *(
            Coords(row=boundary.destination_row, col=boundary.destination_col)
            for boundary in incoming_boundaries
        ),
    }
    known_access_coords = set()
    for coords in entry_coords:
        tiles = _build_connection_tiles(warps, map_memory)
        if not (0 <= coords.row < tiles.shape[0] and 0 <= coords.col < tiles.shape[1]):
            continue
        tiles[coords.row, coords.col] = AsciiTile.PLAYER
        known_access_coords.update(
            get_accessible_coords(coords, tiles, map_memory.blockages, hm_tiles)
        )
    arrival_coords = sorted(
        {
            *(_coords(warp) for warp in warps),
            *(
                Coords(row=boundary.destination_row, col=boundary.destination_col)
                for boundary in incoming_boundaries
            ),
        },
        key=lambda coords: (coords.row, coords.col),
    )
    await _load_warp_groups(
        (warp.destination_map_id for warp in warps),
        known_map_ids,
        warp_groups_by_map,
    )

    arrivals = []
    for coords in arrival_coords:
        component = get_connection_component(
            arrival_coords=coords,
            warp_groups=warp_groups_by_map[map_id],
            boundaries=boundaries,
            map_memory=map_memory,
            hm_tiles=hm_tiles,
        )
        connections = (
            *(
                _resolve_warp_connection(
                    group,
                    warp_groups_by_map.get(group[0].destination_map_id),
                )
                for group in component.warp_groups
            ),
            *(_resolve_boundary_connection(group) for group in component.boundary_groups),
        )
        arrivals.append(
            MapArrivalInspection(
                arrival_coords=coords,
                has_recorded_access=coords in known_access_coords,
                connections=connections,
                has_unexplored_terrain=component.has_unexplored_terrain,
            )
        )
    return MapInspectionResult(map_id=map_id, arrivals=tuple(arrivals))


async def _load_warp_groups(
    map_ids: Iterable[MapId],
    known_map_ids: frozenset[MapId],
    warp_groups_by_map: dict[MapId, WarpGroups],
) -> None:
    """Load and group each visited map once in the current inspection's local lookup."""
    for map_id in map_ids:
        if map_id in known_map_ids and map_id not in warp_groups_by_map:
            warps = await get_warp_memories_for_map(map_id)
            warp_groups_by_map[map_id] = group_remembered_warps(warps)


def _resolve_warp_connection(
    group: tuple[WarpMemoryRead, ...],
    destination_groups: WarpGroups | None,
) -> ResolvedConnection:
    """Resolve matching landing groups while preserving each entrance's recorded identity."""
    warp = group[0]
    destination_warp_ids = {candidate.destination_warp_id for candidate in group}
    return ResolvedConnection(
        source_map_id=warp.map_id,
        source_coords=tuple(dict.fromkeys(_coords(candidate) for candidate in group)),
        destination_map_id=warp.destination_map_id if destination_groups is not None else None,
        destination_coords=tuple(
            dict.fromkeys(
                _coords(candidate)
                for candidate_group in destination_groups or ()
                if any(candidate.warp_id in destination_warp_ids for candidate in candidate_group)
                for candidate in candidate_group
            )
        ),
        is_warp=True,
        last_used_iteration=max(
            (warp.last_used_iteration for warp in group if warp.last_used_iteration is not None),
            default=None,
        ),
    )


def _resolve_boundary_connection(
    group: tuple[MapBoundaryMemoryRead, ...],
) -> ResolvedConnection:
    """Resolve the complete observed coordinate pairs for a map boundary."""
    boundary = group[0]
    return ResolvedConnection(
        source_map_id=boundary.map_id,
        source_coords=tuple(_coords(candidate) for candidate in group),
        destination_map_id=boundary.destination_map_id,
        destination_coords=tuple(
            Coords(row=candidate.destination_row, col=candidate.destination_col)
            for candidate in group
        ),
        is_warp=False,
    )


def get_connection_component(
    *,
    arrival_coords: Coords,
    warp_groups: WarpGroups,
    boundaries: Sequence[MapBoundaryMemoryRead],
    map_memory: MapMemoryRead,
    hm_tiles: list[AsciiTile],
) -> ConnectionComponent:
    """Find reachable connections and unseen terrain using already-grouped warps."""
    tiles = _build_connection_tiles(
        (warp for group in warp_groups for warp in group),
        map_memory,
    )
    height, width = tiles.shape
    if not (0 <= arrival_coords.row < height and 0 <= arrival_coords.col < width):
        return ConnectionComponent(
            warp_groups=(),
            boundary_groups=(),
            has_unexplored_terrain=False,
        )

    tiles[arrival_coords.row, arrival_coords.col] = AsciiTile.PLAYER
    reachable_coords = get_accessible_coords(
        arrival_coords,
        tiles,
        map_memory.blockages,
        hm_tiles,
    )
    reachable_warp_groups = tuple(
        group for group in warp_groups if any(_coords(warp) in reachable_coords for warp in group)
    )
    boundary_groups = tuple(
        group
        for group in group_map_boundaries(boundaries)
        if any(_coords(boundary) in reachable_coords for boundary in group)
    )
    has_unexplored_terrain = bool(get_exploration_candidates(reachable_coords, tiles))
    return ConnectionComponent(
        warp_groups=reachable_warp_groups,
        boundary_groups=boundary_groups,
        has_unexplored_terrain=has_unexplored_terrain,
    )


def _build_connection_tiles(
    warps: Iterable[WarpMemoryRead],
    map_memory: MapMemoryRead,
) -> np.ndarray:
    """Overlay remembered warp coordinates on persisted terrain."""
    tiles = np.asarray([list(row) for row in map_memory.terrain.splitlines()])
    height, width = tiles.shape
    for warp in warps:
        if 0 <= warp.row < height and 0 <= warp.col < width:
            tiles[warp.row, warp.col] = AsciiTile.WARP
    return tiles


def group_remembered_warps(warps: Sequence[WarpMemoryRead]) -> WarpGroups:
    """Group route records without losing alternatives that share a source warp ID."""
    records = dict(enumerate(sorted(warps, key=lambda warp: warp.warp_id)))
    groups = group_contiguous_warps(
        {
            index: (_coords(warp), warp.destination_map_id, warp.activation)
            for index, warp in records.items()
        }
    )
    return tuple(tuple(records[index] for index in group) for group in groups)


def _coords(connection: WarpMemoryRead | MapBoundaryMemoryRead) -> Coords:
    """Construct coordinates from scalar database fields."""
    return Coords(row=connection.row, col=connection.col)
