"""Business logic for the overworld navigation tool."""

from typing import TYPE_CHECKING

from agent.overworld.navigation import (
    build_routing_data,
    calculate_path_to_target,
    get_spinner_destination,
)
from common.constants import ACTION_RESULT_LABEL, GAME_DIALOG_LABEL
from common.enums import AsciiTile, Button, FacingDirection, MapId
from emulator.control_events import ControlBoundary
from overworld_map.service import record_observed_map_boundary, update_overworld_map

if TYPE_CHECKING:
    import numpy as np

    from common.schemas import Coords
    from emulator.control_events import ControlResult
    from emulator.emulator import Emulator
    from emulator.game_state import GameState
    from memory.rolling_memory.schemas import RollingMemory
    from overworld_map.schemas import OverworldMap


async def navigate(
    *,
    iteration: int,
    emulator: Emulator,
    current_map: OverworldMap,
    rolling_memory: RollingMemory,
    coords: Coords,
) -> str:
    """Navigate to the requested target coordinates."""
    game_state = await emulator.get_game_state()
    hm_tiles = game_state.get_hm_tiles()
    routing_tiles, reachable_list = build_routing_data(current_map, game_state)
    if error := _get_target_error(
        current_map,
        game_state,
        coords,
        frozenset(reachable_list),
        routing_tiles,
    ):
        return _record_result(rolling_memory, error)

    path = calculate_path_to_target(
        game_state.player.coords,
        coords,
        routing_tiles,
        current_map.blockages,
        hm_tiles,
    )
    if not path:
        return _record_result(
            rolling_memory,
            f"Navigation failed. No path found to target coordinates {coords}."
            " This either means that the location is inaccessible, or that I have not"
            " explored enough of the map to reveal the path.",
        )

    starting_map_id = current_map.id
    dialogs: list[str] = []
    for button in path:
        next_tile = _get_next_tile(current_map, button, game_state)
        next_coords = game_state.player.coords + _BUTTON_OFFSETS[button]
        unresolved_spinner = (
            next_tile in AsciiTile.get_spinner_tiles()
            and get_spinner_destination(
                next_coords,
                routing_tiles,
            )
            is None
        )
        if unresolved_spinner:
            result = await _explore_spinner(
                iteration, emulator, current_map, button, coords, game_state
            )
            return _record_result(rolling_memory, result, dialogs=dialogs)
        prev_pos = game_state.player.coords
        control_left_overworld = False
        if next_tile in hm_tiles:
            dialog, boundary, game_state = await _handle_hm_use(emulator, button, game_state)
            control_left_overworld = boundary != ControlBoundary.OVERWORLD_READY
            if dialog:
                dialogs.append(dialog)
        else:
            control_result, game_state = await _press_navigation_step(emulator, button, game_state)
            control_left_overworld = control_result.boundary != ControlBoundary.OVERWORLD_READY

        result = (
            _get_interrupted_result(game_state, coords)
            if control_left_overworld
            else _get_navigation_result(
                game_state,
                prev_pos,
                starting_map_id,
                coords,
            )
        )
        # Can't update the map until we validate above that we haven't switched maps.
        if not control_left_overworld and game_state.map.id == starting_map_id:
            await update_overworld_map(
                iteration,
                game_state,
                current_map,
            )
        if result:
            return _record_result(rolling_memory, result, dialogs=dialogs)
    return _record_result(rolling_memory, f"I reached {coords}.", dialogs=dialogs)


async def _explore_spinner(
    iteration: int,
    emulator: Emulator,
    current_map: OverworldMap,
    button: Button,
    target: Coords,
    game_state: GameState,
) -> str:
    """Traverse an unresolved spinner, record its path, and report its destination."""
    spinner_start = game_state.player.coords
    control_result, game_state = await _press_navigation_step(
        emulator,
        button,
        game_state,
        observe_steps=True,
    )

    previous_observation = None
    for observation in control_result.step_observations:
        observation_key = (observation.map.id, observation.player.coords)
        if observation_key != previous_observation:
            await update_overworld_map(
                iteration,
                observation,
                current_map,
            )
            previous_observation = observation_key

    if game_state.player.coords == spinner_start:
        return f"My navigation to {target} was interrupted at {game_state.player.coords}."
    return (
        f"The spinner carried me to {game_state.player.coords}."
        " Navigation stopped so I can plan a new route from here."
    )


def _get_target_error(
    current_map: OverworldMap,
    game_state: GameState,
    coords: Coords,
    accessible_coords: frozenset[Coords],
    routing_tiles: np.ndarray,
) -> str | None:
    """Return why the target coordinates are invalid, if applicable."""
    if game_state.player.is_biking:
        return "I can't navigate while riding a bike."
    if (
        coords.row < 0
        or coords.col < 0
        or coords.row >= current_map.height
        or coords.col >= current_map.width
    ):
        return (
            f"I can't navigate to {coords} because those coordinates are outside the current"
            " map bounds, and the navigation tool can't cross map boundaries."
        )
    if coords == game_state.player.coords:
        return f"Navigation skipped because I am already at {coords}."
    return _get_map_target_error(
        game_state,
        coords,
        accessible_coords,
        routing_tiles,
    )


def _get_next_tile(current_map: OverworldMap, button: Button, game_state: GameState) -> AsciiTile:
    """Get the next tile type that the player will move to."""
    tile_arr = current_map.terrain_ndarray
    player_pos = game_state.player.coords
    if button == Button.UP:
        return tile_arr[player_pos.row - 1, player_pos.col]
    if button == Button.DOWN:
        return tile_arr[player_pos.row + 1, player_pos.col]
    if button == Button.LEFT:
        return tile_arr[player_pos.row, player_pos.col - 1]
    return tile_arr[player_pos.row, player_pos.col + 1]


async def _press_navigation_step(
    emulator: Emulator,
    button: Button,
    game_state: GameState,
    *,
    observe_steps: bool = False,
) -> tuple[ControlResult, GameState]:
    """Complete one movement step, including turning or Pikachu yielding, and return its state."""
    desired_direction = _BUTTON_DIRECTIONS[button]
    if game_state.player.direction != desired_direction:
        result, observed_state = await _press_and_record_boundary(
            emulator,
            button,
            game_state,
            observe_steps=observe_steps,
        )
        if (
            result.boundary != ControlBoundary.OVERWORLD_READY
            or observed_state.player.coords != game_state.player.coords
            or observed_state.player.direction != desired_direction
        ):
            return result, observed_state
        game_state = observed_state

    pikachu_was_ahead = (
        game_state.pikachu.is_rendered
        and game_state.player.coords + _BUTTON_OFFSETS[button] == game_state.pikachu.coords
    )
    result, observed_state = await _press_and_record_boundary(
        emulator,
        button,
        game_state,
        observe_steps=observe_steps,
    )
    if (
        result.boundary == ControlBoundary.OVERWORLD_READY
        and observed_state.player.coords == game_state.player.coords
        and pikachu_was_ahead
    ):
        result, observed_state = await _press_and_record_boundary(
            emulator,
            button,
            observed_state,
            observe_steps=observe_steps,
        )
    return result, observed_state


async def _handle_hm_use(
    emulator: Emulator,
    button: Button,
    game_state: GameState,
) -> tuple[str, ControlBoundary, GameState]:
    """Use a field move and return its dialog, control boundary, and resulting state."""
    if game_state.player.is_surfing:
        result, game_state = await _press_navigation_step(emulator, button, game_state)
        return "", result.boundary, game_state

    # Rotate to face the target.
    if game_state.player.direction != _BUTTON_DIRECTIONS[button]:
        result, game_state = await _press_and_record_boundary(emulator, button, game_state)
        if result.boundary != ControlBoundary.OVERWORLD_READY:
            return "", result.boundary, game_state

    await emulator.press_button(Button.A)
    dialogs = [await emulator.advance_text_dialog()]

    # A valid field move stops at a yes/no menu. A rejected Surf attempt closes the
    # interaction directly, so only confirm when the menu is still on screen.
    if (await emulator.get_game_state()).is_text_on_screen():
        await emulator.press_button(Button.A)
        dialogs.append(await emulator.advance_text_dialog_until_overworld_ready())
    else:
        await emulator.wait_for_overworld_ready()

    game_state = await emulator.get_game_state()
    if not game_state.player.is_surfing:  # Starting to surf moves the player automatically.
        result, game_state = await _press_navigation_step(emulator, button, game_state)
        boundary = result.boundary
    else:
        boundary = ControlBoundary.OVERWORLD_READY
    return " ".join(dialog for dialog in dialogs if dialog), boundary, game_state


async def _press_and_record_boundary(
    emulator: Emulator,
    button: Button,
    previous: GameState,
    *,
    observe_steps: bool = False,
) -> tuple[ControlResult, GameState]:
    """Press once and retain a directly caused, validated map-boundary crossing."""
    result = await emulator.press_overworld_button(
        button,
        observe_steps=observe_steps,
    )
    current = await emulator.get_game_state()
    await record_observed_map_boundary(
        button=button,
        previous=previous,
        result=result,
        current=current,
    )
    return result, current


def _get_navigation_result(
    game_state: GameState,
    prev_pos: Coords,
    starting_map_id: MapId,
    target_pos: Coords,
) -> str | None:
    """Return the result when navigation should stop, if applicable."""
    new_pos = game_state.player.coords
    if game_state.map.id != starting_map_id:
        return (
            f"Map changed from {starting_map_id.name} {prev_pos}"
            f" to {game_state.map.id.name} {new_pos}."
        )
    if new_pos == target_pos:
        return f"I reached {target_pos}."
    if prev_pos == new_pos:
        return f"My navigation to {target_pos} was interrupted at position {new_pos}."
    return None


def _get_interrupted_result(game_state: GameState, target_pos: Coords) -> str:
    """Report that normal overworld control changed domains during navigation."""
    return f"My navigation to {target_pos} was interrupted at position {game_state.player.coords}."


def _record_result(
    rolling_memory: RollingMemory, result: str, *, dialogs: list[str] | None = None
) -> str:
    """Record and return one coherent navigation result."""
    dialog_results = [f'{GAME_DIALOG_LABEL} "{dialog}"' for dialog in dialogs or []]
    action_result = f"{ACTION_RESULT_LABEL} {result}"
    complete_result = "\n\n".join([*dialog_results, action_result])
    rolling_memory.add_memory(complete_result)
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


def _get_map_target_error(
    game_state: GameState,
    coords: Coords,
    accessible_coords: frozenset[Coords],
    routing_tiles: np.ndarray,
) -> str | None:
    """Explain why an in-bounds map coordinate is not a valid local target."""
    target_tile = routing_tiles[coords.row, coords.col]
    if target_tile == AsciiTile.SPRITE:
        return (
            f"Navigation failed. The target coordinates {coords} are occupied by a sprite."
            " If I want to interact with the sprite, I have to navigate to a tile adjacent"
            " to it and then use the button tool to interact with it."
        )
    if target_tile == AsciiTile.UNSEEN:
        return (
            f"Navigation failed. The target coordinates {coords} are still unexplored, so no"
            " revealed route to them exists yet. I should navigate to a listed exploration"
            " candidate to reveal more of the current map."
        )
    traversable_tiles = set(AsciiTile.get_walkable_tiles()) | set(game_state.get_hm_tiles())
    if target_tile not in traversable_tiles:
        return (
            f"Navigation failed. The target coordinates {coords} are revealed but are not a"
            " currently traversable tile. I should choose a reachable walkable coordinate."
        )
    if coords not in accessible_coords:
        return (
            f"Navigation failed. The revealed target coordinates {coords} are outside my"
            " current reachable map region. The navigation tool only moves within this"
            " region and is working as intended. Another area of the same map may require me"
            " to leave through a reachable warp or map boundary and re-enter elsewhere. I"
            " can also continue exploring if the revealed terrain may still connect."
        )
    return None
