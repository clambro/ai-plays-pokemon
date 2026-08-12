"""Business logic for the overworld navigation tool."""

from typing import TYPE_CHECKING

from agent.overworld.tools.navigate import utils
from common.enums import AsciiTile, Button, FacingDirection, MapId
from overworld_map.service import update_overworld_map

if TYPE_CHECKING:
    from common.schemas import Coords
    from emulator.emulator import Emulator
    from emulator.game_state import GameState
    from memory.rolling_memory.schemas import RollingMemory
    from overworld_map.schemas import OverworldMap


class NavigationService:
    """The service for the navigation action.

    This handles emulator interactions for navigation. The pathfinding algorithms are in the
    ``utils`` module.
    """

    def __init__(
        self,
        iteration: int,
        emulator: Emulator,
        current_map: OverworldMap,
        rolling_memory: RollingMemory,
    ) -> None:
        """Initialize the navigation service."""
        self.iteration = iteration
        self.emulator = emulator
        self.current_map = current_map
        self.rolling_memory = rolling_memory

    async def navigate(self, coords: Coords) -> str:
        """Navigate to the requested target coordinates."""
        game_state = await self.emulator.get_game_state()
        hm_tiles = game_state.get_hm_tiles()
        accessible_coords = utils.get_accessible_coords(
            game_state.player.coords,
            self.current_map,
            hm_tiles,
        )
        if error := self._get_target_error(game_state, coords, accessible_coords):
            return self._record_result(error)

        path = utils.calculate_path_to_target(
            game_state.player.coords,
            coords,
            self.current_map,
            hm_tiles,
        )
        if not path:
            return self._record_result(
                f"Navigation failed. No path found to target coordinates {coords}."
                f" This either means that the location is inaccessible, or that I have not"
                f" explored enough of the map to reveal the path.",
            )

        starting_map_id = self.current_map.id
        await self._handle_pikachu(path[0])
        for button in path:
            next_tile = self._get_next_tile(button, game_state)
            next_coords = game_state.player.coords + _BUTTON_OFFSETS[button]
            unresolved_spinner = (
                next_tile in AsciiTile.get_spinner_tiles()
                and utils.get_spinner_destination(
                    next_coords,
                    self.current_map.ascii_tiles_ndarray,
                )
                is None
            )
            if unresolved_spinner:
                result = await self._explore_spinner(button, coords, game_state)
                return self._record_result(result)
            if next_tile in hm_tiles:
                await self._handle_hm_use(button, game_state)
            else:
                await self.emulator.press_button(button)

            prev_pos = game_state.player.coords
            game_state = await self.emulator.get_game_state()
            if result := self._get_navigation_result(
                game_state,
                prev_pos,
                starting_map_id,
                coords,
            ):
                return self._record_result(result)
            # Can't update the map until we validate above that we haven't switched maps.
            await update_overworld_map(
                self.iteration,
                game_state,
                self.current_map,
            )
        return self._record_result(f"Completed navigation to {coords}.")

    async def _explore_spinner(
        self,
        button: Button,
        target: Coords,
        game_state: GameState,
    ) -> str:
        """Traverse an unresolved spinner, record its path, and report its destination."""
        if game_state.player.direction != _BUTTON_DIRECTIONS[button]:
            await self.emulator.press_button(button, wait_for_animation=False)
            game_state = await self.emulator.wait_for_animation_to_finish()

        spinner_start = game_state.player.coords
        observations = []
        await self.emulator.press_button(button, wait_for_animation=False)
        game_state = await self.emulator.wait_for_animation_to_finish(
            on_game_state=observations.append,
        )

        previous_observation = None
        for observation in observations:
            observation_key = (observation.map.id, observation.player.coords)
            if observation_key != previous_observation:
                await update_overworld_map(
                    self.iteration,
                    observation,
                    self.current_map,
                )
                previous_observation = observation_key

        if game_state.player.coords == spinner_start:
            return f"Navigation to {target} interrupted at position {game_state.player.coords}."
        return (
            f"The spinner carried me to {game_state.player.coords}."
            " Navigation stopped so I can plan a new route from here."
        )

    def _get_target_error(
        self,
        game_state: GameState,
        coords: Coords,
        accessible_coords: list[Coords],
    ) -> str | None:
        """Return why the target coordinates are invalid, if applicable."""
        if game_state.player.is_biking:
            return "Navigation is unavailable while riding a bike."
        if (
            coords.row < 0
            or coords.col < 0
            or coords.row >= self.current_map.height
            or coords.col >= self.current_map.width
        ):
            return (
                f"Navigation failed. The target coordinates {coords} are outside the current"
                f" map bounds. The navigation tool cannot cross map boundaries."
            )
        if coords == game_state.player.coords:
            return f"Navigation skipped because I am already at {coords}."
        if self.current_map.ascii_tiles[coords.row][coords.col] == AsciiTile.SPRITE:
            return (
                f"Navigation failed. The target coordinates {coords} are occupied by a sprite."
                f" If I want to interact with the sprite, I have to navigate to a tile adjacent"
                f" to it and then use the button tool to interact with it."
            )
        if coords not in accessible_coords:
            return (
                f"Navigation failed. The target coordinates {coords} cannot be reached from my"
                " current position."
            )
        return None

    async def _handle_pikachu(self, button: Button) -> None:
        """Check if Pikachu is in the way and face it if so.

        Pikachu can block your path on the very first step of navigation if you are not facing it
        when you try to move.
        """
        game_state = await self.emulator.get_game_state()
        if not game_state.pikachu.is_rendered:
            return

        player_pos = game_state.player.coords
        facing = game_state.player.direction
        pikachu_pos = game_state.pikachu.coords
        if (
            button == Button.UP
            and player_pos.row == pikachu_pos.row + 1
            and facing != FacingDirection.UP
        ):
            await self.emulator.press_button(Button.UP)
        elif (
            button == Button.DOWN
            and player_pos.row == pikachu_pos.row - 1
            and facing != FacingDirection.DOWN
        ):
            await self.emulator.press_button(Button.DOWN)
        elif (
            button == Button.LEFT
            and player_pos.col == pikachu_pos.col + 1
            and facing != FacingDirection.LEFT
        ):
            await self.emulator.press_button(Button.LEFT)
        elif (
            button == Button.RIGHT
            and player_pos.col == pikachu_pos.col - 1
            and facing != FacingDirection.RIGHT
        ):
            await self.emulator.press_button(Button.RIGHT)

    def _get_next_tile(self, button: Button, game_state: GameState) -> AsciiTile:
        """Get the next tile type that the player will move to."""
        tile_arr = self.current_map.ascii_tiles_ndarray
        player_pos = game_state.player.coords
        if button == Button.UP:
            return tile_arr[player_pos.row - 1, player_pos.col]
        if button == Button.DOWN:
            return tile_arr[player_pos.row + 1, player_pos.col]
        if button == Button.LEFT:
            return tile_arr[player_pos.row, player_pos.col - 1]
        return tile_arr[player_pos.row, player_pos.col + 1]

    async def _handle_hm_use(self, button: Button, game_state: GameState) -> None:
        """Handle using an HM to access a tile."""
        if game_state.player.is_surfing:
            await self.emulator.press_button(button)
            return  # Already surfing. Just continue normally.

        facing = game_state.player.direction

        # Rotate to face the target.
        if button == Button.UP and facing != FacingDirection.UP:
            await self.emulator.press_button(Button.UP)
        elif button == Button.DOWN and facing != FacingDirection.DOWN:
            await self.emulator.press_button(Button.DOWN)
        elif button == Button.LEFT and facing != FacingDirection.LEFT:
            await self.emulator.press_button(Button.LEFT)
        elif button == Button.RIGHT and facing != FacingDirection.RIGHT:
            await self.emulator.press_button(Button.RIGHT)

        # Use the HM, which takes exactly four button presses for both cut and surf.
        for _ in range(4):
            await self.emulator.press_button(Button.A)
        await self.emulator.wait_for_animation_to_finish()  # Extra time for the HM use animation.

        game_state = await self.emulator.get_game_state()
        if not game_state.player.is_surfing:  # Starting to surf moves the player automatically.
            await self.emulator.press_button(button)

    @staticmethod
    def _get_navigation_result(
        game_state: GameState,
        prev_pos: Coords,
        starting_map_id: MapId,
        target_pos: Coords,
    ) -> str | None:
        """Return the result when navigation should stop, if applicable."""
        new_pos = game_state.player.coords
        if new_pos == target_pos:
            return f"Completed navigation to {target_pos}."
        if prev_pos == new_pos:
            return f"Navigation to {target_pos} interrupted at position {new_pos}."
        if game_state.map.id != starting_map_id:
            return "The map has changed during navigation. Cancelling further steps."
        return None

    def _record_result(self, result: str) -> str:
        """Record and return one coherent navigation result."""
        self.rolling_memory.add_memory(result)
        return result


_BUTTON_OFFSETS = {
    Button.UP: (-1, 0),
    Button.DOWN: (1, 0),
    Button.LEFT: (0, -1),
    Button.RIGHT: (0, 1),
}

_BUTTON_DIRECTIONS = {
    Button.UP: FacingDirection.UP,
    Button.DOWN: FacingDirection.DOWN,
    Button.LEFT: FacingDirection.LEFT,
    Button.RIGHT: FacingDirection.RIGHT,
}
