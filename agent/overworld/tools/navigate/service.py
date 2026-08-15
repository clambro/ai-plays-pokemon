"""Business logic for the overworld navigation tool."""

from typing import TYPE_CHECKING

from agent.overworld import navigation
from agent.overworld.map_view import build_current_map_view
from common.enums import AsciiTile, Button, FacingDirection, MapId
from emulator.control_events import ControlBoundary
from overworld_map.service import update_overworld_map

if TYPE_CHECKING:
    import numpy as np

    from common.schemas import Coords
    from emulator.control_events import ControlResult
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
        map_view = build_current_map_view(self.current_map, game_state)
        navigation_tiles = map_view.navigation_tiles
        if error := self._get_target_error(
            game_state,
            coords,
            map_view.reachable_coords,
            navigation_tiles,
        ):
            return self._record_result(error)

        path = navigation.calculate_path_to_target(
            game_state.player.coords,
            coords,
            navigation_tiles,
            self.current_map.blockages,
            hm_tiles,
        )
        if not path:
            return self._record_result(
                f"Navigation failed. No path found to target coordinates {coords}."
                " This either means that the location is inaccessible, or that I have not"
                " explored enough of the map to reveal the path.",
            )

        starting_map_id = self.current_map.id
        dialogs: list[str] = []
        if not await self._handle_pikachu(path[0]):
            game_state = await self.emulator.get_game_state()
            return self._record_result(
                self._get_interrupted_result(game_state, coords),
            )
        game_state = await self.emulator.get_game_state()
        for button in path:
            next_tile = self._get_next_tile(button, game_state)
            next_coords = game_state.player.coords + _BUTTON_OFFSETS[button]
            unresolved_spinner = (
                next_tile in AsciiTile.get_spinner_tiles()
                and navigation.get_spinner_destination(
                    next_coords,
                    navigation_tiles,
                )
                is None
            )
            if unresolved_spinner:
                result = await self._explore_spinner(button, coords, game_state)
                return self._record_result(result, dialogs=dialogs)
            control_left_overworld = False
            if next_tile in hm_tiles:
                dialog, boundary = await self._handle_hm_use(button, game_state)
                control_left_overworld = boundary != ControlBoundary.OVERWORLD_READY
                if dialog:
                    dialogs.append(dialog)
            else:
                control_result = await self._press_navigation_step(button, game_state)
                control_left_overworld = control_result.boundary != ControlBoundary.OVERWORLD_READY

            prev_pos = game_state.player.coords
            game_state = await self.emulator.get_game_state()
            result = (
                self._get_interrupted_result(game_state, coords)
                if control_left_overworld
                else self._get_navigation_result(
                    game_state,
                    prev_pos,
                    starting_map_id,
                    coords,
                )
            )
            if result:
                return self._record_result(result, dialogs=dialogs)
            # Can't update the map until we validate above that we haven't switched maps.
            await update_overworld_map(
                self.iteration,
                game_state,
                self.current_map,
            )
        return self._record_result(f"I reached {coords}.", dialogs=dialogs)

    async def _explore_spinner(
        self,
        button: Button,
        target: Coords,
        game_state: GameState,
    ) -> str:
        """Traverse an unresolved spinner, record its path, and report its destination."""
        spinner_start = game_state.player.coords
        control_result = await self._press_navigation_step(
            button,
            game_state,
            observe_steps=True,
        )

        previous_observation = None
        for observation in control_result.step_observations:
            observation_key = (observation.map.id, observation.player.coords)
            if observation_key != previous_observation:
                await update_overworld_map(
                    self.iteration,
                    observation,
                    self.current_map,
                )
                previous_observation = observation_key

        game_state = await self.emulator.get_game_state()
        if game_state.player.coords == spinner_start:
            return f"My navigation to {target} was interrupted at {game_state.player.coords}."
        return (
            f"The spinner carried me to {game_state.player.coords}."
            " Navigation stopped so I can plan a new route from here."
        )

    def _get_target_error(
        self,
        game_state: GameState,
        coords: Coords,
        accessible_coords: frozenset[Coords],
        navigation_tiles: np.ndarray,
    ) -> str | None:
        """Return why the target coordinates are invalid, if applicable."""
        if game_state.player.is_biking:
            return "I can't navigate while riding a bike."
        if (
            coords.row < 0
            or coords.col < 0
            or coords.row >= self.current_map.height
            or coords.col >= self.current_map.width
        ):
            return (
                f"I can't navigate to {coords} because those coordinates are outside the current"
                " map bounds, and the navigation tool can't cross map boundaries."
            )
        if coords == game_state.player.coords:
            return f"Navigation skipped because I am already at {coords}."
        if navigation_tiles[coords.row, coords.col] == AsciiTile.SPRITE:
            return (
                f"Navigation failed. The target coordinates {coords} are occupied by a sprite."
                " If I want to interact with the sprite, I have to navigate to a tile adjacent"
                " to it and then use the button tool to interact with it."
            )
        if coords not in accessible_coords:
            return (
                f"Navigation failed. The target coordinates {coords} cannot be reached from my"
                " current position."
            )
        return None

    async def _handle_pikachu(self, button: Button) -> bool:
        """Check if Pikachu is in the way and face it if so.

        Pikachu can block your path on the very first step of navigation if you are not facing it
        when you try to move.
        """
        game_state = await self.emulator.get_game_state()
        if not game_state.pikachu.is_rendered:
            return True

        player_pos = game_state.player.coords
        facing = game_state.player.direction
        pikachu_pos = game_state.pikachu.coords
        needs_pikachu_turn = (
            (
                button == Button.UP
                and player_pos.row == pikachu_pos.row + 1
                and facing != FacingDirection.UP
            )
            or (
                button == Button.DOWN
                and player_pos.row == pikachu_pos.row - 1
                and facing != FacingDirection.DOWN
            )
            or (
                button == Button.LEFT
                and player_pos.col == pikachu_pos.col + 1
                and facing != FacingDirection.LEFT
            )
            or (
                button == Button.RIGHT
                and player_pos.col == pikachu_pos.col - 1
                and facing != FacingDirection.RIGHT
            )
        )
        if not needs_pikachu_turn:
            return True
        control_result = await self.emulator.press_overworld_button(button)
        return control_result.boundary == ControlBoundary.OVERWORLD_READY

    def _get_next_tile(self, button: Button, game_state: GameState) -> AsciiTile:
        """Get the next tile type that the player will move to."""
        tile_arr = self.current_map.terrain_ndarray
        player_pos = game_state.player.coords
        if button == Button.UP:
            return tile_arr[player_pos.row - 1, player_pos.col]
        if button == Button.DOWN:
            return tile_arr[player_pos.row + 1, player_pos.col]
        if button == Button.LEFT:
            return tile_arr[player_pos.row, player_pos.col - 1]
        return tile_arr[player_pos.row, player_pos.col + 1]

    async def _press_navigation_step(
        self,
        button: Button,
        game_state: GameState,
        *,
        observe_steps: bool = False,
    ) -> ControlResult:
        """Complete one movement step, including a required turn or Pikachu yield."""
        result = await self.emulator.press_overworld_button(
            button,
            observe_steps=observe_steps,
        )
        if result.boundary != ControlBoundary.OVERWORLD_READY:
            return result

        desired_direction = _BUTTON_DIRECTIONS[button]
        pikachu_was_ahead = (
            game_state.pikachu.is_rendered
            and game_state.player.coords + _BUTTON_OFFSETS[button] == game_state.pikachu.coords
        )
        if game_state.player.direction == desired_direction and not pikachu_was_ahead:
            return result

        observed_state = await self.emulator.get_game_state()
        if observed_state.player.coords != game_state.player.coords:
            return result

        turned_without_moving = (
            game_state.player.direction != desired_direction
            and observed_state.player.direction == desired_direction
        )
        if turned_without_moving or pikachu_was_ahead:
            result = await self.emulator.press_overworld_button(
                button,
                observe_steps=observe_steps,
            )
        return result

    async def _handle_hm_use(
        self,
        button: Button,
        game_state: GameState,
    ) -> tuple[str, ControlBoundary]:
        """Use a field move and return the dialog produced by the interaction."""
        if game_state.player.is_surfing:
            result = await self._press_navigation_step(button, game_state)
            return "", result.boundary

        # Rotate to face the target.
        if game_state.player.direction != _BUTTON_DIRECTIONS[button]:
            result = await self.emulator.press_overworld_button(button)
            if result.boundary != ControlBoundary.OVERWORLD_READY:
                return "", result.boundary

        await self.emulator.pulse_button(Button.A)
        dialogs = [await self.emulator.advance_text_dialog()]

        # A valid field move stops at a yes/no menu. A rejected Surf attempt closes the
        # interaction directly, so only confirm when the menu is still on screen.
        if (await self.emulator.get_game_state()).is_text_on_screen():
            await self.emulator.pulse_button(Button.A)
            dialogs.append(await self.emulator.advance_text_dialog_until_overworld_ready())
        else:
            await self.emulator.wait_for_overworld_ready()

        game_state = await self.emulator.get_game_state()
        if not game_state.player.is_surfing:  # Starting to surf moves the player automatically.
            result = await self._press_navigation_step(button, game_state)
            boundary = result.boundary
        else:
            boundary = ControlBoundary.OVERWORLD_READY
        return " ".join(dialog for dialog in dialogs if dialog), boundary

    @staticmethod
    def _get_navigation_result(
        game_state: GameState,
        prev_pos: Coords,
        starting_map_id: MapId,
        target_pos: Coords,
    ) -> str | None:
        """Return the result when navigation should stop, if applicable."""
        new_pos = game_state.player.coords
        if game_state.map.id != starting_map_id:
            return f"Map changed from {starting_map_id.name} to {game_state.map.id.name}."
        if new_pos == target_pos:
            return f"I reached {target_pos}."
        if prev_pos == new_pos:
            return f"My navigation to {target_pos} was interrupted at position {new_pos}."
        return None

    @staticmethod
    def _get_interrupted_result(game_state: GameState, target_pos: Coords) -> str:
        """Report that normal overworld control changed domains during navigation."""
        return (
            f"My navigation to {target_pos} was interrupted at position {game_state.player.coords}."
        )

    def _record_result(self, result: str, *, dialogs: list[str] | None = None) -> str:
        """Record and return one coherent navigation result."""
        dialog_results = [f'I read: "{dialog}"' for dialog in dialogs or []]
        complete_result = "\n\n".join([*dialog_results, result])
        self.rolling_memory.add_memory(complete_result)
        return complete_result


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
