from datetime import datetime

from loguru import logger

from agent.schemas import NavigationArgs
from common.constants import FREE_TILE, GRASS_TILE, LEDGE_TILE, PIKACHU_TILE, WARP_TILE
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
from emulator.game_state import YellowLegacyGameState
from overworld_map.schemas import OverworldMap
from overworld_map.service import add_remove_map_entities, update_overworld_map_tiles
from raw_memory.schemas import RawMemory, RawMemoryPiece

# TODO: This service doesn't handle surfing at all.
# TODO: Should avoid grass tiles when possible.
WALKABLE_TILES = {
    GRASS_TILE,
    FREE_TILE,
    WARP_TILE,
    PIKACHU_TILE,
}


class NavigationService:
    """The service for the navigation action."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        current_map: OverworldMap,
        raw_memory: RawMemory,
        args: NavigationArgs,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.current_map = current_map
        self.raw_memory = raw_memory
        self.coords = args

    async def navigate(self) -> None:
        """Navigate to the given coordinates."""
        if not self._validate_target_coords():
            logger.warning("Cancelling navigation due to invalid target coordinates.")
            return

        game_state = await self.emulator.get_game_state()
        path = self._calculate_path_to_target(game_state)
        if not path:
            logger.warning("No path found to target coordinates.")
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    timestamp=datetime.now(),
                    content=(
                        f"Navigation failed. No walkable path found to target coordinates"
                        f" {self.coords}."
                    ),
                ),
            )
            return

        for button in path:
            current_pos = (game_state.player.y, game_state.player.x)
            await self.emulator.press_buttons([button])
            await self.emulator.wait_for_animation_to_finish()

            game_state = await self.emulator.get_game_state()
            self.current_map = await add_remove_map_entities(game_state, self.current_map)
            self.current_map = await update_overworld_map_tiles(game_state, self.current_map)

            new_pos = (game_state.player.y, game_state.player.x)
            if current_pos == new_pos:
                logger.warning("Navigation interrupted. Cancelling.")
                self.raw_memory.append(
                    RawMemoryPiece(
                        iteration=self.iteration,
                        timestamp=datetime.now(),
                        content=(
                            f"Navigation to {self.coords} interrupted at position {current_pos}."
                        ),
                    ),
                )
                return

    def _validate_target_coords(self) -> bool:
        """Validate the target coordinates."""
        if (
            self.coords.row < 0
            or self.coords.col < 0
            or self.coords.row >= self.current_map.width
            or self.coords.col >= self.current_map.height
        ):
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    timestamp=datetime.now(),
                    content=(
                        f"Navigation failed. Target coordinates {self.coords} are outside of the"
                        f" {self.current_map.id.name} map boundary."
                    ),
                ),
            )
            return False

        target_tile = self.current_map.ascii_tiles_ndarray[self.coords.row, self.coords.col]
        if target_tile not in WALKABLE_TILES:
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    timestamp=datetime.now(),
                    content=(
                        f"Navigation failed. Target coordinates {self.coords} are on a non-walkable"
                        f' tile of type "{target_tile}".'
                    ),
                ),
            )
            return False

        return True

    def _calculate_path_to_target(self, game_state: YellowLegacyGameState) -> list[Button] | None:
        """
        Calculate the path to the target coordinates as a list of button presses using the A*
        algorithm.
        """
        start_pos = (game_state.player.y, game_state.player.x)
        target_pos = (self.coords.row, self.coords.col)

        def _get_distance(a: tuple[int, int], b: tuple[int, int]) -> float:
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def _get_neighbors(pos: tuple[int, int]) -> list[tuple[int, int]]:
            y, x = pos
            neighbors = []
            for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_y, new_x = y + dy, x + dx
                if 0 <= new_y < self.current_map.height and 0 <= new_x < self.current_map.width:
                    target_tile = self.current_map.ascii_tiles_ndarray[new_y, new_x]
                    if target_tile in WALKABLE_TILES:
                        neighbors.append((new_y, new_x))
                    elif target_tile == LEDGE_TILE and dy == 1:
                        # Account for the fact that we can jump down ledges, skipping a tile.
                        neighbors.append((new_y + 1, new_x))
            return neighbors

        open_set = {start_pos}
        came_from = {}
        g_score = {start_pos: 0}
        f_score = {start_pos: _get_distance(start_pos, target_pos)}

        while open_set:
            current = min(open_set, key=lambda pos: f_score.get(pos, float("inf")))

            if current == target_pos:
                # Reconstruct path and convert to button presses
                path = []
                while current in came_from:
                    prev = came_from[current]
                    # Calculate direction
                    dy = current[0] - prev[0]
                    dx = current[1] - prev[1]

                    # Convert direction to button
                    if dy > 0:
                        path.append(Button.DOWN)
                    elif dy < 0:
                        path.append(Button.UP)
                    elif dx > 0:
                        path.append(Button.RIGHT)
                    elif dx < 0:
                        path.append(Button.LEFT)

                    current = prev

                return list(reversed(path))  # Reverse to get start->target order

            open_set.remove(current)

            for neighbor in _get_neighbors(current):
                tentative_g_score = g_score[current] + 1

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + _get_distance(neighbor, target_pos)
                    open_set.add(neighbor)

        # If we get here, no path was found
        return None
