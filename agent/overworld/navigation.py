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
) -> list[Button] | None:
    """Calculate an A* path to the target as a sequence of button presses.

    Args:
        start_pos: Coordinate at which to begin the path.
        target_pos: Coordinate the path should reach.
        tiles: Current navigation tiles.
        rules: Movement constraints beyond the displayed tile symbols.

    Returns:
        Button presses reaching the target, or ``None`` when no path exists.
    """
    open_set = {start_pos}
    came_from: dict[Coords, tuple[Coords, Button]] = {}
    g_score = {start_pos: 0}
    f_score = {start_pos: (start_pos - target_pos).length}
    expensive_tiles = [
        AsciiTile.GRASS,
        AsciiTile.CUT_TREE,
        AsciiTile.WATER,
        *AsciiTile.get_spinner_tiles(),
    ]

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
            # Bias movement away from tiles that take more time to traverse.
            increment = 5 if tiles[neighbor.row, neighbor.col] in expensive_tiles else 1
            tentative_g_score = g_score[current] + increment

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = (current, button)
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + (neighbor - target_pos).length
                open_set.add(neighbor)

    # If we get here, no path was found
    return None
