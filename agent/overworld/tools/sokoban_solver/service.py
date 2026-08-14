"""Business logic for the overworld Sokoban solver tool."""

import asyncio
from typing import TYPE_CHECKING

from agent.overworld.tools.sokoban_solver.schemas import SokobanMap
from common.enums import AsciiTile, BlockedDirection, Button, FacingDirection, SpriteLabel
from common.schemas import Coords
from overworld_map.views import get_navigation_tiles

if TYPE_CHECKING:
    from emulator.emulator import Emulator
    from emulator.game_state import GameState
    from memory.rolling_memory.schemas import RollingMemory
    from overworld_map.schemas import OverworldMap

FREE_TILE = "F"
WALL_TILE = "W"
WARP_TILE = "P"


class SokobanSolverService:
    """Solve the Sokoban puzzle."""

    def __init__(
        self,
        emulator: Emulator,
        current_map: OverworldMap,
        rolling_memory: RollingMemory,
    ) -> None:
        """Initialize the sokoban solver service."""
        self.emulator = emulator
        self.current_map = current_map
        self.rolling_memory = rolling_memory

    async def solve(self) -> str:
        """Solve the Sokoban puzzle."""
        game_state, collision_tiles = await self.emulator.get_game_state_with_map_collision_tiles()
        sokoban_map = self._get_simplified_map(game_state)

        if not sokoban_map.boulders or not sokoban_map.goals:
            result = "I couldn't run the Sokoban solver because there were no boulders or goals."
            self.rolling_memory.add_memory(result)
            return result

        sokoban_map.collision_tiles = collision_tiles
        solution = self._solve_sokoban(sokoban_map, game_state)

        if solution is None:
            result = (
                "The Sokoban solver was unable to find a solution. This is likely because I"
                " haven't explored enough of the map yet, or I need to get boulders from"
                " other locations first, or because I already solved the puzzle previously."
            )
            self.rolling_memory.add_memory(result)
            return result

        result = await self._execute_solution(solution, sokoban_map)
        self.rolling_memory.add_memory(result)
        return result

    def _get_simplified_map(self, game_state: GameState) -> SokobanMap:
        """Get a simplified map of the Sokoban puzzle with the boulders and goals."""
        navigation_tiles = get_navigation_tiles(self.current_map, game_state)
        boulders = {
            sprite.coords
            for entity_id in self.current_map.known_sprite_ids
            if (sprite := game_state.sprites.get(entity_id)) is not None
            and sprite.label == SpriteLabel.BOULDER
            and sprite.is_rendered
        }
        simplified_tiles = []
        goals = set()
        for row_idx, row in enumerate(navigation_tiles):
            simplified_row = []
            for col_idx, t in enumerate(row):
                terrain = self.current_map.terrain[row_idx][col_idx]
                if t == AsciiTile.BOULDER_HOLE or terrain == AsciiTile.PRESSURE_PLATE:
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

    def _solve_sokoban(
        self,
        sokoban_map: SokobanMap,
        game_state: GameState,
    ) -> list[Button] | None:
        """Solve the Sokoban puzzle using breadth-first search.

        The search is deliberately simple because Pokémon's Sokoban state spaces are small.
        """
        initial_state = (game_state.player.coords, frozenset(sokoban_map.boulders))

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
                    current_player_pos,
                    new_player_pos,
                    sokoban_map,
                    game_state,
                    is_boulder=False,
                ):
                    continue

                button = _DIRECTION_TO_BUTTON_MAP[direction]
                if new_player_pos in current_boulders:  # Pushing a boulder.
                    new_boulder_pos = new_player_pos + direction
                    is_boulder_tile_free = self._is_movement_possible(
                        current_player_pos,
                        new_boulder_pos,
                        sokoban_map,
                        game_state,
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
        source: Coords,
        destination: Coords,
        sokoban_map: SokobanMap,
        game_state: GameState,
        *,
        is_boulder: bool,
    ) -> bool:
        """Check if a destination is valid (within bounds, walkable, and not blocked)."""
        if (
            destination.row < 0
            or destination.row >= len(sokoban_map.tiles)
            or destination.col < 0
            or destination.col >= len(sokoban_map.tiles[0])
        ):
            return False

        if is_boulder:
            if not game_state.map.is_boulder_push_terrain_legal(
                sokoban_map.collision_tiles,
                source,
                destination,
            ):
                return False
        else:
            direction = destination - source
            if self._is_blocked(source, direction.row, direction.col):
                return False

        valid_tiles = (FREE_TILE,)
        if is_boulder:
            # Boulders can be pushed onto warp tiles, but the player should avoid them.
            valid_tiles += (WARP_TILE,)
        return sokoban_map.tiles[destination.row][destination.col] in valid_tiles

    async def _execute_solution(self, solution: list[Button], sokoban_map: SokobanMap) -> str:
        """Execute the solution by pressing buttons."""
        is_strength_active = False
        strength_dialog = ""
        for button in solution:
            game_state = await self.emulator.get_game_state()
            next_pos = game_state.player.coords + _BUTTON_TO_DIRECTION_MAP[button]

            if not is_strength_active and next_pos in sokoban_map.boulders:
                await self._face_next_pos(button, game_state)
                # Hand dialog progression to the ROM-event driver immediately after activation.
                await self.emulator.press_button(
                    Button.A,
                    wait_for_animation=False,
                )
                strength_dialog = await self.emulator.advance_text_dialog()
                is_strength_active = True
            elif next_pos == game_state.pikachu.coords:
                # We have to face Pikachu before we can walk through it.
                await self._face_next_pos(button, game_state)

            await self.emulator.press_button(button)
            if next_pos in sokoban_map.boulders:
                sokoban_map.boulders.remove(next_pos)
                sokoban_map.boulders.add(next_pos + _BUTTON_TO_DIRECTION_MAP[button])
                # The boulders have a slow, irregular animation, so we add an extra wait.
                await asyncio.sleep(1)

            next_game_state = await self.emulator.get_game_state()
            if (
                next_game_state.player.coords == game_state.player.coords
                and next_game_state.sprites == game_state.sprites
            ):
                return _include_dialog(
                    "The Sokoban solver was interrupted because my movement was blocked.",
                    strength_dialog,
                )

        return _include_dialog("I executed the Sokoban solution.", strength_dialog)

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
        game_state: GameState,
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


def _include_dialog(result: str, dialog: str) -> str:
    """Include captured field-move dialog in the first-person action result."""
    sections = [f'I read: "{dialog}"'] if dialog else []
    return "\n\n".join([*sections, result])


_BUTTON_TO_DIRECTION_MAP = {
    Button.RIGHT: Coords(row=0, col=1),
    Button.LEFT: Coords(row=0, col=-1),
    Button.DOWN: Coords(row=1, col=0),
    Button.UP: Coords(row=-1, col=0),
}
_DIRECTION_TO_BUTTON_MAP = {v: k for k, v in _BUTTON_TO_DIRECTION_MAP.items()}
