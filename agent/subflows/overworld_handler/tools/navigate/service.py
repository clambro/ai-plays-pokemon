"""Business logic for navigate in the overworld subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.overworld_handler.tools.navigate import utils
from common.enums import AsciiTile, Button, FacingDirection, MapId
from overworld_map.service import update_map_with_screen_info

if TYPE_CHECKING:
    from common.schemas import Coords
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from memory.rolling_memory import RollingMemory
    from overworld_map.schemas import OverworldMap


class NavigationService:
    """The service for the navigation action.

    This handles emulator interactions for navigation. The pathfinding algorithms are in the
    ``utils`` module.
    """

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        current_map: OverworldMap,
        rolling_memory: RollingMemory,
    ) -> None:
        """Initialize the navigation service."""
        self.iteration = iteration
        self.emulator = emulator
        self.current_map = current_map
        self.rolling_memory = rolling_memory

    async def navigate(self, coords: Coords) -> tuple[OverworldMap, RollingMemory]:
        """Navigate to the requested target coordinates."""
        self.rolling_memory.add_memory(content=f"Navigating to {coords}.")
        game_state = await self.emulator.get_game_state()
        hm_tiles = game_state.get_hm_tiles()
        accessible_coords = utils.get_accessible_coords(
            game_state.player.coords,
            self.current_map,
            hm_tiles,
        )
        if not self._validate_target_coords(game_state, coords, accessible_coords):
            logger.warning("Cancelling navigation due to invalid target coordinates.")
            return self.current_map, self.rolling_memory

        path = utils.calculate_path_to_target(
            game_state.player.coords,
            coords,
            self.current_map,
            hm_tiles,
        )
        if not path:
            logger.warning("No path found to target coordinates.")
            self.rolling_memory.add_memory(
                content=(
                    f"Navigation failed. No path found to target coordinates {coords}."
                    f" This either means that the location is inaccessible, or that I have not"
                    f" explored enough of the map to reveal the path."
                ),
            )
            return self.current_map, self.rolling_memory

        starting_map_id = self.current_map.id
        await self._handle_pikachu(path[0])
        for button in path:
            next_tile = self._get_next_tile(button, game_state)
            if next_tile in hm_tiles:
                await self._handle_hm_use(button, game_state)
            else:
                await self.emulator.press_button(button)

            prev_pos = game_state.player.coords
            game_state = await self.emulator.get_game_state()
            if self._should_cancel_navigation(game_state, prev_pos, starting_map_id, coords):
                return self.current_map, self.rolling_memory
            # Can't update the map until we validate above that we haven't switched maps.
            self.current_map = await update_map_with_screen_info(
                self.iteration,
                game_state,
                self.current_map,
            )
        return self.current_map, self.rolling_memory

    def _validate_target_coords(
        self,
        game_state: YellowLegacyGameState,
        coords: Coords,
        accessible_coords: list[Coords],
    ) -> bool:
        """Validate the target coordinates. Return True if the coordinates are valid."""
        if (
            coords.row < 0
            or coords.col < 0
            or coords.row >= self.current_map.height
            or coords.col >= self.current_map.width
        ):
            self.rolling_memory.add_memory(
                content=(
                    f"Navigation failed. The target coordinates {coords} are outside the current"
                    f" map bounds. The navigation tool cannot cross map boundaries."
                ),
            )
            return False
        if coords == game_state.player.coords:
            self.rolling_memory.add_memory(
                content=f"I tried to navigate to {coords}, but I'm already there!",
            )
            return False
        if self.current_map.ascii_tiles[coords.row][coords.col] == AsciiTile.SPRITE:
            self.rolling_memory.add_memory(
                content=(
                    f"Navigation failed. The target coordinates {coords} are occupied by a sprite."
                    f" If I want to interact with the sprite, I have to navigate to a tile adjacent"
                    f" to it and then use the button tool to interact with it."
                ),
            )
            return False
        if coords not in accessible_coords:
            self.rolling_memory.add_memory(
                content=(
                    f"Navigation failed. The target coordinates {coords} are not in the list of"
                    f" accessible coordinates that was provided to me."
                ),
            )
            return False
        return True

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

    def _get_next_tile(self, button: Button, game_state: YellowLegacyGameState) -> AsciiTile:
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

    async def _handle_hm_use(self, button: Button, game_state: YellowLegacyGameState) -> None:
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

    def _should_cancel_navigation(
        self,
        game_state: YellowLegacyGameState,
        prev_pos: Coords,
        starting_map_id: MapId,
        target_pos: Coords,
    ) -> bool:
        """Check if we should cancel navigation."""
        new_pos = game_state.player.coords
        if new_pos == target_pos:
            self.rolling_memory.add_memory(
                content=f"Completed navigation to {target_pos}.",
            )
            return True
        if prev_pos == new_pos:
            logger.warning("Navigation interrupted. Cancelling.")
            self.rolling_memory.add_memory(
                content=f"Navigation to {target_pos} interrupted at position {new_pos}.",
            )
            return True
        if game_state.map.id != starting_map_id:
            logger.warning("Map changed during navigation. Cancelling.")
            self.rolling_memory.add_memory(
                content="The map has changed during navigation. Cancelling further steps.",
            )
            return True
        return False
