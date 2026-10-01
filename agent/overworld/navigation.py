"""Target pathfinding for agent overworld navigation."""

from typing import TYPE_CHECKING

from common.enums import AsciiTile, Button
from overworld_map.traversal import get_neighbors

if TYPE_CHECKING:
    import numpy as np

    from common.schemas import Coords
    from overworld_map.schemas import TraversalRules


def calculate_path_to_target(
    start_pos: Coords,
    target_pos: Coords,
    tiles: np.ndarray,
    rules: TraversalRules,
    *,
    is_surfing: bool,
) -> list[Button] | None:
    """Calculate an A* path to the target as a sequence of button presses.

    Args:
        start_pos: Coordinate at which to begin the path.
        target_pos: Coordinate the path should reach.
        tiles: Current navigation tiles.
        rules: Movement constraints beyond the displayed tile symbols.
        is_surfing: Whether the player is already surfing at the start.

    Returns:
        Button presses reaching the target, or ``None`` when no path exists.
    """
    open_set = {start_pos}
    came_from: dict[Coords, tuple[Coords, Button]] = {}
    g_score = {start_pos: 0}
    f_score = {start_pos: (start_pos - target_pos).length}

    while open_set:
        current = min(open_set, key=lambda pos: f_score.get(pos, float("inf")))

        if current == target_pos:
            # Reconstruct path and convert to button presses
            path = []
            while current in came_from:
                prev, button = came_from[current]
                path.append(button)
                current = prev

            return list(reversed(path))  # Reverse to get start->target order

        open_set.remove(current)

        for neighbor, button in get_neighbors(current, tiles, rules):
            neighbor_tile = tiles[neighbor.row, neighbor.col]
            is_entering_water = neighbor_tile == AsciiTile.WATER and (
                not is_surfing
                if current == start_pos
                else tiles[current.row, current.col] != AsciiTile.WATER
            )
            if is_entering_water or neighbor_tile == AsciiTile.CUT_TREE:
                increment = 10  # These require a dialog. Avoid if possible.
            elif neighbor_tile in [AsciiTile.GRASS, *AsciiTile.get_spinner_tiles()]:
                increment = 5  # These can slow us down. Avoid if possible, but better than dialog.
            else:
                increment = 1
            tentative_g_score = g_score[current] + increment

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = (current, button)
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + (neighbor - target_pos).length
                open_set.add(neighbor)

    # If we get here, no path was found
    return None
