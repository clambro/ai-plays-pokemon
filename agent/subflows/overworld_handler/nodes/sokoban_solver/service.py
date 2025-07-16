import asyncio

from loguru import logger

from agent.subflows.overworld_handler.nodes.sokoban_solver.schemas import SokobanMap
from common.enums import AsciiTile, BlockedDirection, Button, FacingDirection, SpriteLabel
from common.schemas import Coords
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from memory.raw_memory import RawMemory
from overworld_map.schemas import OverworldMap

FREE_TILE = "F"
WALL_TILE = "W"
WARP_TILE = "P"


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
            logger.warning("No boulders or goals found in Sokoban map. Bailing.")
            return  # This shouldn't happen, but we need the option to bail if it does.

        # This can get expensive, so we run it on its own thread.
        solution = await asyncio.to_thread(self._solve_sokoban, sokoban_map)

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
            if sprite.label == SpriteLabel.BOULDER and sprite.is_rendered
        }
        simplified_tiles = []
        goals = set()
        for row_idx, row in enumerate(ascii_tiles):
            simplified_row = []
            for col_idx, t in enumerate(row):
                if t in (AsciiTile.BOULDER_HOLE, AsciiTile.PRESSURE_PLATE):
                    goals.add(Coords(row=row_idx, col=col_idx))

                if t in (AsciiTile.WARP, AsciiTile.BOULDER_HOLE):
                    simplified_row.append(WARP_TILE)
                elif t in AsciiTile.get_walkable_tiles():
                    simplified_row.append(FREE_TILE)
                else:
                    simplified_row.append(WALL_TILE)
            simplified_tiles.append(simplified_row)
        for b in boulders:
            simplified_tiles[b.row][b.col] = FREE_TILE

        return SokobanMap(tiles=simplified_tiles, boulders=boulders, goals=goals)

    def _solve_sokoban(self, sokoban_map: SokobanMap) -> list[Button] | None:
        """
        Solve the Sokoban puzzle using BFS on the state space. This could be optimized, but the
        state spaces in Pokemon are small and simple enough that this is likely fine.
        """
        player_pos = self.emulator.get_game_state().player.coords
        initial_state = (player_pos, frozenset(sokoban_map.boulders))

        queue = [(initial_state, [])]
        visited = {initial_state}

        while queue:
            (current_player_pos, current_boulders), path = queue.pop(0)
            if current_boulders & sokoban_map.goals:  # At least one goal is solved.
                return path

            # There's thankfully no special neighbour logic here. Unlike the general navigation
            # service, the Sokoban puzzles never involve spinner tiles, surfing, or ledges.
            for direction in [
                Coords(row=0, col=1),
                Coords(row=1, col=0),
                Coords(row=0, col=-1),
                Coords(row=-1, col=0),
            ]:
                new_player_pos = current_player_pos + direction
                if not self._is_movement_possible(
                    new_player_pos,
                    direction,
                    sokoban_map,
                    is_boulder=False,
                ):
                    continue

                button = _DIRECTION_TO_BUTTON_MAP[direction]
                if new_player_pos in current_boulders:  # Pushing a boulder.
                    new_boulder_pos = new_player_pos + direction
                    is_boulder_tile_free = self._is_movement_possible(
                        new_boulder_pos,
                        direction,
                        sokoban_map,
                        is_boulder=True,
                    )
                    if new_boulder_pos in current_boulders or not is_boulder_tile_free:
                        continue  # Push is illegal.

                    new_boulders = set(current_boulders)
                    new_boulders.remove(new_player_pos)
                    new_boulders.add(new_boulder_pos)
                    # Pushing a boulder doesn't change the player's position!
                    new_state = (current_player_pos, frozenset(new_boulders))

                    if new_state not in visited:
                        visited.add(new_state)
                        queue.append((new_state, [*path, button]))

                else:  # Regular walking.
                    new_state = (new_player_pos, current_boulders)
                    if new_state not in visited:
                        visited.add(new_state)
                        queue.append((new_state, [*path, button]))

        return None  # No solution found.

    def _is_movement_possible(
        self,
        pos: Coords,
        direction: Coords,
        sokoban_map: SokobanMap,
        *,
        is_boulder: bool,
    ) -> bool:
        """Check if a position is valid (within bounds, walkable, and not blocked)."""
        if (
            pos.row < 0
            or pos.row >= len(sokoban_map.tiles)
            or pos.col < 0
            or pos.col >= len(sokoban_map.tiles[0])
            or self._is_blocked(pos, direction.row, direction.col)
        ):
            return False
        valid_tiles = (FREE_TILE,)
        if is_boulder:
            # Boulders can be pushed onto warp tiles, but the player should avoid them.
            valid_tiles += (WARP_TILE,)
        return sokoban_map.tiles[pos.row][pos.col] in valid_tiles

    async def _execute_solution(self, solution: list[Button], sokoban_map: SokobanMap) -> None:
        """Execute the solution by pressing buttons."""
        is_strength_active = False
        for button in solution:
            game_state = self.emulator.get_game_state()
            next_pos = game_state.player.coords + _BUTTON_TO_DIRECTION_MAP[button]

            if not is_strength_active and next_pos in sokoban_map.boulders:
                await self._face_next_pos(button, game_state)
                await self.emulator.press_button(Button.A)  # Activate strength.
                await self.emulator.press_button(Button.B)  # Dismiss the dialog box.
                await self.emulator.press_button(Button.B)
                await self.emulator.press_button(Button.B)
                is_strength_active = True
            elif next_pos == game_state.pikachu.coords:
                # We have to face Pikachu before we can walk through it.
                await self._face_next_pos(button, game_state)

            await self.emulator.press_button(button)
            if next_pos in sokoban_map.boulders:
                sokoban_map.boulders.remove(next_pos)
                sokoban_map.boulders.add(next_pos + _BUTTON_TO_DIRECTION_MAP[button])
                # The boulders have an irregular animation, so we add an extra wait.
                await self.emulator.wait_for_animation_to_finish()

            next_game_state = self.emulator.get_game_state()
            if (
                next_game_state.player.coords == game_state.player.coords
                and next_game_state.sprites == game_state.sprites
            ):
                self.raw_memory.add_memory(
                    iteration=self.iteration,
                    content="Sokoban solver was interrupted. Skipping further execution.",
                )
                return
            next_game_state = game_state

        self.raw_memory.add_memory(
            iteration=self.iteration,
            content="Successfully executed a Sokoban solution.",
        )

    def _is_blocked(self, current: Coords, dy: int, dx: int) -> bool:
        """Check if the movement is blocked by a paired tile collision."""
        blockages = self.current_map.blockages.get(current)
        if not blockages:
            return False
        if dy == 1:
            return bool(blockages & BlockedDirection.DOWN)
        if dy == -1:
            return bool(blockages & BlockedDirection.UP)
        if dx == 1:
            return bool(blockages & BlockedDirection.RIGHT)
        if dx == -1:
            return bool(blockages & BlockedDirection.LEFT)
        return False

    async def _face_next_pos(
        self,
        button: Button,
        game_state: YellowLegacyGameState,
    ) -> None:
        """Face the next position."""
        if (
            (button == Button.RIGHT and game_state.player.direction != FacingDirection.RIGHT)
            or (button == Button.LEFT and game_state.player.direction != FacingDirection.LEFT)
            or (button == Button.DOWN and game_state.player.direction != FacingDirection.DOWN)
            or (button == Button.UP and game_state.player.direction != FacingDirection.UP)
        ):
            # Skipping the wait here ensures that we pivot instead of walking.
            await self.emulator.press_button(button, wait_for_animation=False)
            await self.emulator.wait_for_animation_to_finish()


_BUTTON_TO_DIRECTION_MAP = {
    Button.RIGHT: Coords(row=0, col=1),
    Button.LEFT: Coords(row=0, col=-1),
    Button.DOWN: Coords(row=1, col=0),
    Button.UP: Coords(row=-1, col=0),
}
_DIRECTION_TO_BUTTON_MAP = {v: k for k, v in _BUTTON_TO_DIRECTION_MAP.items()}
