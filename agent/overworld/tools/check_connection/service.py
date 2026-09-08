"""Check remembered map connectivity without navigating the player."""

from typing import TYPE_CHECKING

import numpy as np
from loguru import logger

from agent.overworld.connections import group_contiguous_warps, group_map_boundaries
from agent.overworld.navigation import get_accessible_coords, get_exploration_candidates
from agent.overworld.tools.check_connection.schemas import (
    ConnectionCheckError,
    ConnectionCheckResult,
    ResolvedConnection,
)
from common.enums import AsciiTile, MapId
from common.schemas import Coords
from database.map_boundary_memory.repository import get_map_boundary_memories_for_map
from database.map_memory.repository import get_map_memory, get_visited_maps
from database.warp_memory.repository import get_warp_memories_for_map
from database.warp_memory.schemas import WarpMemoryRead

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Sequence

    from agent.overworld.tools.check_connection.schemas import SourceConnection, WarpGroups
    from database.map_boundary_memory.schemas import MapBoundaryMemoryRead
    from database.map_memory.schemas import MapMemoryRead


async def check_connection(
    *,
    map_name: str,
    coordinates: Coords,
    hm_tiles: list[AsciiTile],
) -> ConnectionCheckResult | ConnectionCheckError:
    """Resolve a remembered connection and its arrival region without producing text."""
    try:
        source_map_id = MapId[map_name]
    except KeyError:
        return ConnectionCheckError.INVALID_MAP
    if source_map_id in {MapId.OUTSIDE, MapId.UNKNOWN}:
        return ConnectionCheckError.UNSUPPORTED_MAP

    try:
        return await _check_connection(
            source_map_id=source_map_id,
            coordinates=coordinates,
            hm_tiles=hm_tiles,
        )
    except Exception as error:  # noqa: BLE001
        logger.opt(exception=error).warning(
            "Connection check failed; continuing without remembered connectivity."
        )
        return ConnectionCheckError.MEMORY_UNAVAILABLE


async def _check_connection(
    *,
    source_map_id: MapId,
    coordinates: Coords,
    hm_tiles: list[AsciiTile],
) -> ConnectionCheckResult | ConnectionCheckError:
    """Locate the source, then inspect either kind of connection through the same workflow."""
    known_map_ids = frozenset(await get_visited_maps())
    if source_map_id not in known_map_ids:
        return ConnectionCheckError.UNVISITED_MAP

    source_warps = await get_warp_memories_for_map(source_map_id)
    source = await _find_source_connection(source_map_id, coordinates, source_warps)
    if source is None:
        return ConnectionCheckError.UNKNOWN_CONNECTION

    warp_groups_by_map = {source_map_id: group_remembered_warps(source_warps)}
    source_record = source if isinstance(source, WarpMemoryRead) else source[0]
    destination_map_id = source_record.destination_map_id
    destination_map = (
        await get_map_memory(destination_map_id) if destination_map_id in known_map_ids else None
    )
    if destination_map is not None:
        await _load_warp_groups([destination_map_id], known_map_ids, warp_groups_by_map)
    connection, arrival_coords = _resolve_entry(
        source,
        warp_groups_by_map[source_record.map_id],
        warp_groups_by_map.get(destination_map_id) if destination_map is not None else None,
    )
    if destination_map is None or arrival_coords is None:
        return ConnectionCheckResult(connection=connection)

    boundaries = await get_map_boundary_memories_for_map(destination_map_id)
    warp_groups, boundary_groups, has_unexplored_terrain = get_connection_component(
        arrival_coords=arrival_coords,
        warp_groups=warp_groups_by_map[destination_map_id],
        boundaries=boundaries,
        map_memory=destination_map,
        hm_tiles=hm_tiles,
    )
    if isinstance(source, WarpMemoryRead):
        warp_groups = tuple(
            group
            for group in warp_groups
            if all(warp.warp_id != source.destination_warp_id for warp in group)
        )
    else:
        boundary_groups = tuple(
            group
            for group in boundary_groups
            if group[0].destination_map_id != source_record.map_id
        )

    await _load_warp_groups(
        (group[0].destination_map_id for group in warp_groups),
        known_map_ids,
        warp_groups_by_map,
    )
    other_connections = (
        *(
            _resolve_warp_connection(
                group,
                warp_groups_by_map.get(group[0].destination_map_id),
                destination_warp_ids={warp.destination_warp_id for warp in group},
            )
            for group in warp_groups
        ),
        *(
            _resolve_boundary_connection(group, destination_visited=True)
            for group in boundary_groups
        ),
    )
    return ConnectionCheckResult(
        connection=connection,
        other_connections=other_connections,
        has_unexplored_terrain=has_unexplored_terrain,
    )


async def _find_source_connection(
    map_id: MapId,
    coordinates: Coords,
    warps: Sequence[WarpMemoryRead],
) -> SourceConnection | None:
    """Prefer a warp at the requested coordinate, otherwise find its remembered boundary."""
    warp = next((warp for warp in warps if _coords(warp) == coordinates), None)
    if warp is not None:
        return warp
    boundaries = await get_map_boundary_memories_for_map(map_id)
    return next(
        (
            group
            for group in group_map_boundaries(boundaries)
            if any(_coords(boundary) == coordinates for boundary in group)
        ),
        None,
    )


async def _load_warp_groups(
    map_ids: Iterable[MapId],
    known_map_ids: frozenset[MapId],
    warp_groups_by_map: dict[MapId, WarpGroups],
) -> None:
    """Load and group each visited map once in the current check's local lookup."""
    for map_id in map_ids:
        if map_id in known_map_ids and map_id not in warp_groups_by_map:
            warps = await get_warp_memories_for_map(map_id)
            warp_groups_by_map[map_id] = group_remembered_warps(warps)


def _resolve_entry(
    source: SourceConnection,
    source_warp_groups: WarpGroups,
    destination_warp_groups: WarpGroups | None,
) -> tuple[ResolvedConnection, Coords | None]:
    """Resolve the checked endpoints and retain the actual tile used for arrival."""
    if isinstance(source, WarpMemoryRead):
        source_group = next(group for group in source_warp_groups if source in group)
        connection = _resolve_warp_connection(
            source_group,
            destination_warp_groups,
            destination_warp_ids={source.destination_warp_id},
        )
        arrival_coords = next(
            (
                _coords(warp)
                for group in destination_warp_groups or ()
                for warp in group
                if warp.warp_id == source.destination_warp_id
            ),
            None,
        )
        return connection, arrival_coords

    return (
        _resolve_boundary_connection(
            source,
            destination_visited=destination_warp_groups is not None,
        ),
        Coords(row=source[0].destination_row, col=source[0].destination_col),
    )


def _resolve_warp_connection(
    group: tuple[WarpMemoryRead, ...],
    destination_groups: WarpGroups | None,
    *,
    destination_warp_ids: Collection[int],
) -> ResolvedConnection:
    """Resolve matching landing groups while preserving each entrance's recorded identity."""
    warp = group[0]
    return ResolvedConnection(
        source_map_id=warp.map_id,
        source_coords=tuple(_coords(candidate) for candidate in group),
        destination_map_id=warp.destination_map_id if destination_groups is not None else None,
        destination_coords=tuple(
            _coords(candidate)
            for candidate_group in destination_groups or ()
            if any(candidate.warp_id in destination_warp_ids for candidate in candidate_group)
            for candidate in candidate_group
        ),
        is_warp=True,
        last_used_iteration=max(
            (warp.last_used_iteration for warp in group if warp.last_used_iteration is not None),
            default=None,
        ),
    )


def _resolve_boundary_connection(
    group: tuple[MapBoundaryMemoryRead, ...],
    *,
    destination_visited: bool,
) -> ResolvedConnection:
    """Resolve the complete observed coordinate pairs for a map boundary."""
    boundary = group[0]
    return ResolvedConnection(
        source_map_id=boundary.map_id,
        source_coords=tuple(_coords(candidate) for candidate in group),
        destination_map_id=boundary.destination_map_id if destination_visited else None,
        destination_coords=tuple(
            Coords(row=candidate.destination_row, col=candidate.destination_col)
            for candidate in group
        )
        if destination_visited
        else (),
        is_warp=False,
    )


def get_connection_component(
    *,
    arrival_coords: Coords,
    warp_groups: WarpGroups,
    boundaries: Sequence[MapBoundaryMemoryRead],
    map_memory: MapMemoryRead,
    hm_tiles: list[AsciiTile],
) -> tuple[
    WarpGroups,
    tuple[tuple[MapBoundaryMemoryRead, ...], ...],
    bool,
]:
    """Find reachable connections and unseen terrain using already-grouped warps."""
    tiles = _build_connection_tiles(
        (warp for group in warp_groups for warp in group),
        map_memory,
    )
    height, width = tiles.shape
    if not (0 <= arrival_coords.row < height and 0 <= arrival_coords.col < width):
        return (), (), False

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
    return reachable_warp_groups, boundary_groups, has_unexplored_terrain


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
    """Apply shared entrance grouping while retaining the original memory records."""
    warps_by_id = {warp.warp_id: warp for warp in warps}
    groups = group_contiguous_warps(
        {warp.warp_id: (_coords(warp), warp.destination_map_id, warp.activation) for warp in warps}
    )
    return tuple(tuple(warps_by_id[warp_id] for warp_id in group) for group in groups)


def _coords(connection: WarpMemoryRead | MapBoundaryMemoryRead) -> Coords:
    """Construct coordinates from scalar database fields."""
    return Coords(row=connection.row, col=connection.col)
