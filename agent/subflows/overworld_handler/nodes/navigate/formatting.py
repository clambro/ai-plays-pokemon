"""
Formatting utilities for navigation operations.

This module contains the formatting functions for navigation operations, separate from any
algorithmic logic to make them easier to test.
"""

from itertools import groupby

from common.enums import FacingDirection
from common.schemas import Coords
from overworld_map.schemas import OverworldMap


def format_coordinates_grid(coordinates: list[Coords]) -> str:
    """
    Format a list of coordinates as a grid string with rows separated by newlines so the LLM has
    an easier time parsing it.

    [(0,0), (0,1), (1,0), (1,1), (1,2)]
    ->
    (0,0) (0,1)
    (1,0) (1,1) (1,2)
    """
    if not coordinates:
        return ""

    coordinates = sorted(coordinates, key=lambda c: (c.row, c.col))
    rows = []
    for _, row_coords in groupby(coordinates, key=lambda c: c.row):
        row_str = ", ".join(str(coord) for coord in row_coords)
        rows.append(row_str)

    return "\n".join(rows)


def format_exploration_candidates(candidates: list[Coords]) -> str:
    """
    Format exploration candidates for LLM consumption.

    :param candidates: List of exploration candidate coordinates
    :return: Formatted string for LLM
    """
    if not candidates:
        return "No exploration candidates found."

    return format_coordinates_grid(candidates)


def format_map_boundary_tiles(
    boundary_tiles: dict[FacingDirection, list[Coords]],
    map_data: OverworldMap,
) -> str:
    """
    Format map boundary tiles for LLM consumption.

    :param boundary_tiles: Dictionary mapping directions to boundary coordinates
    :param map_connections: Dictionary mapping directions to connected map IDs
    :return: Formatted string for LLM
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
                f" boundary at the far {cardinal_dir} of the current map."
            )

    return "\n".join(output)
