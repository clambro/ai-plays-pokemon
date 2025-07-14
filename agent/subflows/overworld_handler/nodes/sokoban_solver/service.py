from collections import deque

from agent.subflows.overworld_handler.nodes.sokoban_solver.schemas import SokobanMap
from common.enums import AsciiTile, Button, SpriteLabel
from common.schemas import Coords
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory
from overworld_map.schemas import OverworldMap

FREE_TILE = "F"
WALL_TILE = "W"


class SokobanSolverService:
    """Solve the Sokoban puzzle."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        current_map: OverworldMap,
        raw_memory: RawMemory,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.current_map = current_map
        self.raw_memory = raw_memory

    async def solve(self) -> None:
        """Solve the Sokoban puzzle."""
        sokoban_map = self._get_simplified_map()

        if not sokoban_map.boulders or not sokoban_map.goals:
            return  # This shouldn't happen, but we need the option to bail if it does.

        solution = await self._solve_sokoban(sokoban_map)
        if not solution:
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=(
                    "The Sokoban solver was unable to find a solution. This is likely because I"
                    " haven't explored enough of the map yet, or I need to get boulders from"
                    " other locations first, or because I already solved the puzzle previously."
                ),
            )
            return

        await self._execute_solution(solution, sokoban_map)

    def _get_simplified_map(self) -> SokobanMap:
        """Get a simplified map of the Sokoban puzzle with the boulders and goals."""
        ascii_tiles = self.current_map.ascii_tiles
        boulders = {
            sprite.coords
            for sprite in self.current_map.known_sprites.values()
            if sprite.label == SpriteLabel.BOULDER
        }
        simplified_tiles = []
        goals = set()
        for row_idx, row in enumerate(ascii_tiles):
            simplified_row = []
            for col_idx, t in enumerate(row):
                if t in (AsciiTile.BOULDER_HOLE, AsciiTile.PRESSURE_PLATE):
                    goals.add(Coords(row=row_idx, col=col_idx))
                if t in AsciiTile.get_walkable_tiles():
                    simplified_row.append(FREE_TILE)
                else:
                    simplified_row.append(WALL_TILE)
            simplified_tiles.append(simplified_row)

        return SokobanMap(tiles=simplified_tiles, boulders=boulders, goals=goals)

    async def _solve_sokoban(self, sokoban_map: SokobanMap) -> list[Button] | None:
        """
        Solve the Sokoban puzzle using BFS on the state space. This could be optimized, but the
        state spaces in Pokemon are small and simple enough that this is fine.
        """
        player_pos = self.emulator.get_game_state().player.coords
        initial_state = (player_pos, frozenset(sokoban_map.boulders))

        queue = deque([(initial_state, [])])
        visited = {initial_state}

        while queue:
            (current_player_pos, current_boulders), path = queue.popleft()
            if current_boulders == sokoban_map.goals:  # Puzzle solved.
                return path

            for direction in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                button = _DIRECTION_TO_BUTTON_MAP[direction]
                new_player_pos = current_player_pos + direction
                if not self._is_tile_free(new_player_pos, sokoban_map):
                    continue

                if new_player_pos in current_boulders:  # Pushing a boulder.
                    new_boulder_pos = new_player_pos + direction
                    is_boulder_tile_free = self._is_tile_free(new_boulder_pos, sokoban_map)
                    if new_boulder_pos not in current_boulders and is_boulder_tile_free:
                        new_boulders = set(current_boulders)
                        new_boulders.remove(new_player_pos)
                        new_boulders.add(new_boulder_pos)
                        new_state = (new_player_pos, frozenset(new_boulders))

                        if new_state not in visited:
                            visited.add(new_state)
                            queue.append((new_state, [*path, button]))
                else:  # Regular walking.
                    new_state = (new_player_pos, current_boulders)
                    if new_state not in visited:
                        visited.add(new_state)
                        queue.append((new_state, [*path, button]))

        return None  # No solution found.

    def _is_tile_free(self, pos: Coords, sokoban_map: SokobanMap) -> bool:
        """Check if a position is valid (within bounds and walkable)."""
        if (
            pos.row < 0
            or pos.row >= len(sokoban_map.tiles)
            or pos.col < 0
            or pos.col >= len(sokoban_map.tiles[0])
        ):
            return False
        return sokoban_map.tiles[pos.row][pos.col] == FREE_TILE

    async def _execute_solution(self, solution: list[Button], sokoban_map: SokobanMap) -> None:
        """Execute the solution by pressing buttons."""
        is_strength_active = False
        prev_game_state = self.emulator.get_game_state()
        for button in solution:
            next_pos = prev_game_state.player.coords + _BUTTON_TO_DIRECTION_MAP[button]
            if not is_strength_active and next_pos in sokoban_map.boulders:
                await self.emulator.press_button(Button.A)  # Activate strength.
                await self.emulator.press_button(Button.B)  # Dismiss the dialog box.
                await self.emulator.press_button(Button.B)
                await self.emulator.press_button(Button.B)
                is_strength_active = True

            await self.emulator.press_button(button)
            await self.emulator.wait_for_animation_to_finish()  # Wait for the boulder to move.
            game_state = self.emulator.get_game_state()
            if (
                game_state.player.coords == prev_game_state.player.coords
                and game_state.sprites == prev_game_state.sprites
            ):
                self.raw_memory.add_memory(
                    iteration=self.iteration,
                    content="Sokoban solver was interrupted. Skipping further execution.",
                )
                return
            prev_game_state = game_state

        self.raw_memory.add_memory(
            iteration=self.iteration,
            content="Successfully executed Sokoban solution.",
        )


_BUTTON_TO_DIRECTION_MAP = {
    Button.RIGHT: (0, 1),
    Button.LEFT: (0, -1),
    Button.DOWN: (1, 0),
    Button.UP: (-1, 0),
}
_DIRECTION_TO_BUTTON_MAP = {v: k for k, v in _BUTTON_TO_DIRECTION_MAP.items()}
