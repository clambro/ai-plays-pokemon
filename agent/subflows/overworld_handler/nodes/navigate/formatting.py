"""Formatting utilities for navigation operations.

This module contains the formatting functions for navigation operations, separate from any
algorithmic logic to make them easier to test.
"""

from itertools import groupby
from typing import TYPE_CHECKING

from common.enums import FacingDirection

if TYPE_CHECKING:
    from common.schemas import Coords
    from overworld_map.schemas import OverworldMap


def format_coordinates_grid(coordinates: list[Coords], map_data: OverworldMap) -> str:
    """Format coordinates and their tile types as a grid.

    Rows are separated by newlines so the model can parse their spatial relationship more easily.

    Args:
        coordinates: Map coordinates to include.
        map_data: Explored map containing the tile at each coordinate.

    Returns:
        Rows of coordinate-and-tile tuples, or an empty string when no coordinates are supplied.

    Example:
        [(0,0), (0,1), (1,0), (1,1), (1,2), (2,1)]
        ->
        (0,0,❀) (0,1,∙)
        (1,0,❀) (1,1,❀) (1,2,∙)
        (2,1,❀)
    """
    if not coordinates:
        return ""

    coordinates = sorted(coordinates, key=lambda c: (c.row, c.col))
    rows = []
    for _, row_coords in groupby(coordinates, key=lambda c: c.row):
        row_str = ", ".join(
            f"({c.row}, {c.col}, {map_data.ascii_tiles[c.row][c.col]})" for c in row_coords
        )
        rows.append(row_str)

    return "\n".join(rows)


def format_exploration_candidates(candidates: list[Coords], map_data: OverworldMap) -> str:
    """Format exploration candidates for LLM consumption.

    Args:
        candidates: Coordinates adjacent to unexplored terrain.
        map_data: Explored map containing the tile at each coordinate.

    Returns:
        A coordinate grid for the model, or a message stating that no candidates exist.
    """
    if not candidates:
        return "No exploration candidates found."

    return format_coordinates_grid(candidates, map_data)


def format_map_boundary_tiles(
    boundary_tiles: dict[FacingDirection, list[Coords]],
    map_data: OverworldMap,
) -> str:
    """Format accessible map boundaries for LLM consumption.

    Args:
        boundary_tiles: Accessible boundary coordinates grouped by direction.
        map_data: Explored map containing the connected map IDs.

    Returns:
        Descriptions of discovered connections and whether their boundaries are accessible.
    """
    output = []
    map_connections = {
        FacingDirection.UP: ("NORTH", map_data.north_connection),
        FacingDirection.DOWN: ("SOUTH", map_data.south_connection),
        FacingDirection.RIGHT: ("EAST", map_data.east_connection),
        FacingDirection.LEFT: ("WEST", map_data.west_connection),
    }

    for facing_dir, (cardinal_dir, connection) in map_connections.items():
        if connection is not None and boundary_tiles[facing_dir]:
            coord_str = ", ".join(str(c) for c in boundary_tiles[facing_dir])
            output.append(
                f"The {connection.name} map boundary at the far {cardinal_dir} of the current map"
                f" is accessible from {coord_str}."
            )
        elif connection is not None:
            output.append(
                f"You have not yet discovered a valid path to the {connection.name} map"
                f" boundary at the far {cardinal_dir} of the current map. You can likely find it"
                f" either by visiting more exploration candidates, or perhaps by getting to a new"
                f" part of the current map via an intermediate map (e.g. through a building or"
                f" cave)."
            )

    return "\n".join(output)
