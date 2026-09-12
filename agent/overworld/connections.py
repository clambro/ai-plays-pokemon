"""Pure grouping rules for discovered map connections."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from common.enums import FacingDirection, MapId, WarpActivation
    from common.schemas import Coords
    from database.map_boundary_memory.schemas import MapBoundaryMemoryRead


def group_contiguous_warps(
    warps: Mapping[int, tuple[Coords, MapId, WarpActivation]],
) -> tuple[tuple[int, ...], ...]:
    """Group coincident or adjacent entries sharing a destination map and activation.

    Args:
        warps: One map's entries keyed by ID, with coordinates, destination map, and activation.

    Returns:
        Groups ordered by their lowest entry ID, with IDs sorted within each group.
        Individual landing records do not affect entrance grouping.
    """
    groups = []
    grouped_ids = set()
    for warp_id in sorted(warps):
        if warp_id in grouped_ids:
            continue
        _, destination, activation = warps[warp_id]
        matching_warps = {
            candidate_id: candidate_coords
            for candidate_id, (
                candidate_coords,
                candidate_destination,
                candidate_activation,
            ) in warps.items()
            if candidate_destination == destination and candidate_activation == activation
        }
        group = [warp_id]
        grouped_ids.add(warp_id)
        pending = [warp_id]
        while pending:
            current_coords, _, _ = warps[pending.pop()]
            for candidate_id, candidate_coords in matching_warps.items():
                if candidate_id in grouped_ids:
                    continue
                if (candidate_coords - current_coords).length <= 1:
                    group.append(candidate_id)
                    grouped_ids.add(candidate_id)
                    pending.append(candidate_id)
        groups.append(tuple(sorted(group)))
    return tuple(groups)


def group_map_boundaries(
    boundaries: Sequence[MapBoundaryMemoryRead],
) -> tuple[tuple[MapBoundaryMemoryRead, ...], ...]:
    """Group coordinate pairs by source map, direction, and destination map.

    Preserve group encounter order and sort each group's records by source coordinates.
    """
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
