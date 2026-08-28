"""Check remembered map connectivity without navigating the player."""

from typing import TYPE_CHECKING

import numpy as np
from loguru import logger

from agent.overworld import formatting, navigation
from common.constants import CONNECTION_CHECK_LABEL
from common.enums import AsciiTile, FacingDirection, MapId
from common.schemas import Coords
from database.map_boundary_memory.repository import get_map_boundary_memories_for_map
from database.map_memory.repository import get_map_memory
from database.warp_memory.repository import get_warp_memories_for_map

if TYPE_CHECKING:
    from collections.abc import Sequence

    from database.map_boundary_memory.schemas import MapBoundaryMemoryRead
    from database.map_memory.schemas import MapMemoryRead
    from database.warp_memory.schemas import WarpMemoryRead


async def check_connection(
    *,
    map_name: str,
    coordinates: Coords,
    hm_tiles: list[AsciiTile],
) -> str:
    """Check one remembered connection and describe its destination component."""
    try:
        source_map_id = MapId[map_name]
    except KeyError:
        return f'{CONNECTION_CHECK_LABEL} "{map_name}" is not a known map.'
    if source_map_id in {MapId.OUTSIDE, MapId.UNKNOWN}:
        return f'{CONNECTION_CHECK_LABEL} "{map_name}" cannot have remembered connections.'

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
        return f"{CONNECTION_CHECK_LABEL} Connection memory is currently unavailable."


async def _check_connection(
    *,
    source_map_id: MapId,
    coordinates: Coords,
    hm_tiles: list[AsciiTile],
) -> str:
    """Resolve one valid check entirely from remembered observations."""
    if await get_map_memory(source_map_id) is None:
        return f"{CONNECTION_CHECK_LABEL} {source_map_id.name} has not been visited."

    source_warps = await get_warp_memories_for_map(source_map_id)
    source_warp = next((warp for warp in source_warps if _coords(warp) == coordinates), None)
    if source_warp is not None:
        return await _check_warp(
            source_warp=source_warp,
            source_warps=source_warps,
            hm_tiles=hm_tiles,
        )

    source_boundaries = await get_map_boundary_memories_for_map(source_map_id)
    source_boundary_group = _find_boundary_group(coordinates, source_boundaries)
    if source_boundary_group:
        return await _check_boundary(
            source_group=source_boundary_group,
            hm_tiles=hm_tiles,
        )

    return (
        f"{CONNECTION_CHECK_LABEL} No previously discovered connection is known on "
        f"{source_map_id.name} at {coordinates}."
    )


async def _check_warp(
    *,
    source_warp: WarpMemoryRead,
    source_warps: Sequence[WarpMemoryRead],
    hm_tiles: list[AsciiTile],
) -> str:
    """Follow a remembered warp from one of its physical coordinates."""
    source_map_id = source_warp.map_id
    source_group = next(
        group for group in _group_contiguous_warps(source_warps) if source_warp in group
    )
    destination_map = await get_map_memory(source_warp.destination_map_id)
    if destination_map is None:
        return f"{CONNECTION_CHECK_LABEL} This connection's destination has not been visited."

    destination_warps = await get_warp_memories_for_map(source_warp.destination_map_id)
    arrival_warp = next(
        (warp for warp in destination_warps if warp.warp_id == source_warp.destination_warp_id),
        None,
    )
    if arrival_warp is None:
        return f"{CONNECTION_CHECK_LABEL} This connection's destination has not been discovered."
    arrival_group = next(
        group for group in _group_contiguous_warps(destination_warps) if arrival_warp in group
    )

    destination_boundaries = await get_map_boundary_memories_for_map(destination_map.map_id)
    warp_groups, boundary_groups, has_unexplored_terrain = get_connection_component(
        arrival_coords=_coords(arrival_warp),
        warps=destination_warps,
        boundaries=destination_boundaries,
        map_memory=destination_map,
        hm_tiles=hm_tiles,
    )
    warp_groups = tuple(
        group
        for group in warp_groups
        if all(warp.warp_id != arrival_warp.warp_id for warp in group)
    )
    header = formatting.format_connection(
        source_map_id=source_map_id,
        source_coords=tuple(_coords(warp) for warp in source_group),
        destination_map_id=source_warp.destination_map_id,
        destination_coords=tuple(_coords(warp) for warp in arrival_group),
    )
    return await _format_check_result(
        header=header,
        warp_groups=warp_groups,
        boundary_groups=boundary_groups,
        has_unexplored_terrain=has_unexplored_terrain,
    )


async def _check_boundary(
    *,
    source_group: tuple[MapBoundaryMemoryRead, ...],
    hm_tiles: list[AsciiTile],
) -> str:
    """Follow a remembered outdoor map connection from one of its coordinates."""
    source_map_id = source_group[0].map_id
    source_boundary = source_group[0]
    destination_map = await get_map_memory(source_boundary.destination_map_id)
    if destination_map is None:
        return f"{CONNECTION_CHECK_LABEL} This connection's destination has not been visited."

    destination_warps = await get_warp_memories_for_map(source_boundary.destination_map_id)
    destination_boundaries = await get_map_boundary_memories_for_map(
        source_boundary.destination_map_id
    )
    arrival_coords = Coords(
        row=source_boundary.destination_row,
        col=source_boundary.destination_col,
    )
    warp_groups, boundary_groups, has_unexplored_terrain = get_connection_component(
        arrival_coords=arrival_coords,
        warps=destination_warps,
        boundaries=destination_boundaries,
        map_memory=destination_map,
        hm_tiles=hm_tiles,
    )
    boundary_groups = tuple(
        group for group in boundary_groups if group[0].destination_map_id != source_map_id
    )
    header = formatting.format_connection(
        source_map_id=source_map_id,
        source_coords=tuple(_coords(boundary) for boundary in source_group),
        destination_map_id=source_boundary.destination_map_id,
        destination_coords=tuple(
            Coords(row=boundary.destination_row, col=boundary.destination_col)
            for boundary in source_group
        ),
    )
    return await _format_check_result(
        header=header,
        warp_groups=warp_groups,
        boundary_groups=boundary_groups,
        has_unexplored_terrain=has_unexplored_terrain,
    )


async def _format_check_result(
    *,
    header: str,
    warp_groups: Sequence[tuple[WarpMemoryRead, ...]],
    boundary_groups: Sequence[tuple[MapBoundaryMemoryRead, ...]],
    has_unexplored_terrain: bool,
) -> str:
    """Format the shared result of following one remembered connection."""
    exploration = (
        "Unexplored terrain can still be reached from this arrival region."
        if has_unexplored_terrain
        else "No unexplored terrain is reachable from this arrival region."
    )
    connection_lines = [
        *[await _describe_warp_group(group) for group in warp_groups],
        *(_describe_boundary_group(group) for group in boundary_groups),
    ]
    if not connection_lines:
        return (
            f"{CONNECTION_CHECK_LABEL} {header}\n{exploration}\n"
            "No other discovered connections are reachable from that arrival "
            "point through revealed terrain."
        )

    return (
        f"{CONNECTION_CHECK_LABEL} {header}\n{exploration}\n"
        "Other discovered connections reachable from that arrival point:\n"
        + "\n".join(f"- {line}" for line in connection_lines)
    )


async def _describe_warp_group(group: tuple[WarpMemoryRead, ...]) -> str:
    """Describe all source and destination coordinates of one remembered warp."""
    warp = group[0]
    if await get_map_memory(warp.destination_map_id) is None:
        return formatting.format_connection(
            source_map_id=warp.map_id,
            source_coords=tuple(_coords(candidate) for candidate in group),
            destination_map_id=None,
            destination_coords=(),
        )

    destination_warps = await get_warp_memories_for_map(warp.destination_map_id)
    destination_group = next(
        (
            candidate_group
            for candidate_group in _group_contiguous_warps(destination_warps)
            if any(candidate.warp_id == warp.destination_warp_id for candidate in candidate_group)
        ),
        (),
    )
    return formatting.format_connection(
        source_map_id=warp.map_id,
        source_coords=tuple(_coords(candidate) for candidate in group),
        destination_map_id=warp.destination_map_id,
        destination_coords=tuple(_coords(candidate) for candidate in destination_group),
    )


def _describe_boundary_group(group: tuple[MapBoundaryMemoryRead, ...]) -> str:
    """Describe all source and destination coordinates of one map boundary."""
    boundary = group[0]
    return formatting.format_connection(
        source_map_id=boundary.map_id,
        source_coords=tuple(_coords(candidate) for candidate in group),
        destination_map_id=boundary.destination_map_id,
        destination_coords=tuple(
            Coords(row=candidate.destination_row, col=candidate.destination_col)
            for candidate in group
        ),
    )


def get_connection_component(
    *,
    arrival_coords: Coords,
    warps: Sequence[WarpMemoryRead],
    boundaries: Sequence[MapBoundaryMemoryRead],
    map_memory: MapMemoryRead,
    hm_tiles: list[AsciiTile],
) -> tuple[
    tuple[tuple[WarpMemoryRead, ...], ...],
    tuple[tuple[MapBoundaryMemoryRead, ...], ...],
    bool,
]:
    """Find remembered connections and unseen terrain in one arrival component."""
    tiles = _build_connection_tiles(warps, map_memory)
    height, width = tiles.shape
    if not (0 <= arrival_coords.row < height and 0 <= arrival_coords.col < width):
        return (), (), False

    tiles[arrival_coords.row, arrival_coords.col] = AsciiTile.PLAYER
    reachable_coords = navigation.get_accessible_coords(
        arrival_coords,
        tiles,
        map_memory.blockages,
        hm_tiles,
    )
    warp_groups = tuple(
        group
        for group in _group_contiguous_warps(warps)
        if any(_coords(warp) in reachable_coords for warp in group)
    )
    boundary_groups = tuple(
        group
        for group in _group_boundaries(boundaries)
        if any(_coords(boundary) in reachable_coords for boundary in group)
    )
    has_unexplored_terrain = bool(navigation.get_exploration_candidates(reachable_coords, tiles))
    return warp_groups, boundary_groups, has_unexplored_terrain


def _build_connection_tiles(
    warps: Sequence[WarpMemoryRead],
    map_memory: MapMemoryRead,
) -> np.ndarray:
    """Overlay remembered warp coordinates on persisted terrain."""
    tiles = np.asarray([list(row) for row in map_memory.terrain.splitlines()])
    height, width = tiles.shape
    for warp in warps:
        if 0 <= warp.row < height and 0 <= warp.col < width:
            tiles[warp.row, warp.col] = AsciiTile.WARP
    return tiles


def _find_boundary_group(
    coordinates: Coords,
    boundaries: Sequence[MapBoundaryMemoryRead],
) -> tuple[MapBoundaryMemoryRead, ...]:
    """Find the known map boundary occupying one edge coordinate."""
    groups = _group_boundaries(boundaries)
    return next(
        (group for group in groups if any(_coords(boundary) == coordinates for boundary in group)),
        (),
    )


def _group_contiguous_warps(
    warps: Sequence[WarpMemoryRead],
) -> tuple[tuple[WarpMemoryRead, ...], ...]:
    """Combine adjacent records that represent one logical warp."""
    groups = []
    grouped_ids = set()
    for warp in sorted(warps, key=lambda memory: memory.warp_id):
        if warp.warp_id in grouped_ids:
            continue
        matching_warps = [
            candidate
            for candidate in warps
            if candidate.destination_map_id == warp.destination_map_id
            and candidate.destination_warp_id == warp.destination_warp_id
            and candidate.activation == warp.activation
        ]
        group = [warp]
        grouped_ids.add(warp.warp_id)
        pending = [warp]
        while pending:
            current = pending.pop()
            for candidate in matching_warps:
                if candidate.warp_id in grouped_ids:
                    continue
                if (_coords(candidate) - _coords(current)).length == 1:
                    group.append(candidate)
                    grouped_ids.add(candidate.warp_id)
                    pending.append(candidate)
        groups.append(tuple(sorted(group, key=lambda memory: memory.warp_id)))
    return tuple(groups)


def _group_boundaries(
    boundaries: Sequence[MapBoundaryMemoryRead],
) -> tuple[tuple[MapBoundaryMemoryRead, ...], ...]:
    """Combine coordinate pairs belonging to one logical map boundary."""
    grouped: dict[
        tuple[MapId, FacingDirection, MapId],
        list[MapBoundaryMemoryRead],
    ] = {}
    for boundary in boundaries:
        key = (boundary.map_id, boundary.direction, boundary.destination_map_id)
        grouped.setdefault(key, []).append(boundary)
    return tuple(
        tuple(sorted(group, key=lambda boundary: (boundary.row, boundary.col)))
        for group in grouped.values()
    )


def _coords(connection: WarpMemoryRead | MapBoundaryMemoryRead) -> Coords:
    """Construct coordinates from scalar database fields."""
    return Coords(row=connection.row, col=connection.col)
