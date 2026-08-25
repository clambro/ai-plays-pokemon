"""Business logic for the overworld Sokoban solver tool."""

from typing import TYPE_CHECKING

from agent.overworld.tools.sokoban_solver.schemas import SokobanMap
from common.constants import CAPTURED_DIALOG_MARKER
from common.enums import AsciiTile, BlockedDirection, Button, FacingDirection, SpriteLabel
from common.schemas import Coords
from emulator.control_events import ControlBoundary
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

            activating_strength = not is_strength_active and next_pos in sokoban_map.boulders
            yielding_to_pikachu = next_pos == game_state.pikachu.coords
            if (activating_strength or yielding_to_pikachu) and not await self._face_next_pos(
                button,
                game_state,
            ):
                return _include_dialog(
                    "I stopped the Sokoban solver because control left the overworld.",
                    strength_dialog,
                )

            if activating_strength:
                await self.emulator.press_button(Button.A)
                strength_dialog = await self.emulator.advance_text_dialog_until_overworld_ready()
                is_strength_active = True

            pushing_boulder = next_pos in sokoban_map.boulders
            game_state = await self.emulator.get_game_state()
            if not await self._execute_step(
                button,
                game_state,
                boulder_coords=next_pos if pushing_boulder else None,
            ):
                return _include_dialog(
                    "The Sokoban solver was interrupted because my movement was blocked.",
                    strength_dialog,
                )

            if pushing_boulder:
                sokoban_map.boulders.remove(next_pos)
                sokoban_map.boulders.add(next_pos + _BUTTON_TO_DIRECTION_MAP[button])

        return _include_dialog("I executed the Sokoban solution.", strength_dialog)

    async def _execute_step(
        self,
        button: Button,
        game_state: GameState,
        *,
        boulder_coords: Coords | None,
    ) -> bool:
        """Execute one planned movement, including turning or the two-stage boulder push."""
        starting_coords = game_state.player.coords
        desired_direction = _BUTTON_TO_FACING_DIRECTION[button]
        pikachu_ahead = (
            game_state.pikachu.is_rendered
            and starting_coords + _BUTTON_TO_DIRECTION_MAP[button] == game_state.pikachu.coords
        )
        max_attempts = 3 if boulder_coords is not None else 2

        for attempt in range(max_attempts):
            result = await self.emulator.press_overworld_button(button)
            if result.boundary != ControlBoundary.OVERWORLD_READY:
                return False

            observed_state = await self.emulator.get_game_state()
            if boulder_coords is not None:
                boulder_still_present = any(
                    sprite.label == SpriteLabel.BOULDER
                    and sprite.coords == boulder_coords
                    and sprite.is_rendered
                    for sprite in observed_state.sprites.values()
                )
                if not boulder_still_present:
                    return True
            elif observed_state.player.coords != starting_coords:
                return True

            needs_retry = boulder_coords is not None or (
                attempt == 0 and (game_state.player.direction != desired_direction or pikachu_ahead)
            )
            if not needs_retry:
                return False
        return False

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
    ) -> bool:
        """Face the next position and report whether control remains in the overworld."""
        if game_state.player.direction == _BUTTON_TO_FACING_DIRECTION[button]:
            return True
        result = await self.emulator.press_overworld_button(button)
        return result.boundary == ControlBoundary.OVERWORLD_READY


def _include_dialog(result: str, dialog: str) -> str:
    """Include captured field-move dialog in the first-person action result."""
    sections = [f'{CAPTURED_DIALOG_MARKER} "{dialog}"'] if dialog else []
    return "\n\n".join([*sections, result])


_BUTTON_TO_DIRECTION_MAP = {
    Button.RIGHT: Coords(row=0, col=1),
    Button.LEFT: Coords(row=0, col=-1),
    Button.DOWN: Coords(row=1, col=0),
    Button.UP: Coords(row=-1, col=0),
}
_DIRECTION_TO_BUTTON_MAP = {v: k for k, v in _BUTTON_TO_DIRECTION_MAP.items()}
_BUTTON_TO_FACING_DIRECTION = {
    Button.RIGHT: FacingDirection.RIGHT,
    Button.LEFT: FacingDirection.LEFT,
    Button.DOWN: FacingDirection.DOWN,
    Button.UP: FacingDirection.UP,
}
