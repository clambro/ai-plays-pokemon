"""Use the game's Fly menu to travel to a visited destination."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.utils import move_cursor
from common.constants import ACTION_RESULT_LABEL
from common.enums import Badge, Button, MapId, Tileset
from emulator.control_events import ControlBoundary, ControlHandoff

if TYPE_CHECKING:
    from emulator.emulator import Emulator
    from memory.rolling_memory.schemas import RollingMemory


class FlyError(Exception):
    """The requested flight cannot be completed."""


async def fly(*, rolling_memory: RollingMemory, emulator: Emulator, destination: MapId) -> str:
    """Fly through the ordinary party and town-map menus, then report the resulting map."""
    try:
        result = await _fly(emulator, destination)
    except ControlHandoff:
        raise
    except Exception as error:  # noqa: BLE001
        await _leave_menus(emulator)
        if not isinstance(error, FlyError):
            logger.exception("Unexpected error while using Fly.")
        result = f"I could not fly to {destination.name}. {error}"
    result = f"{ACTION_RESULT_LABEL} {result}"
    rolling_memory.add_memory(result)
    return result


async def _fly(emulator: Emulator, destination: MapId) -> str:
    """Choose a destination only after seeing it in the game's visited-town list."""
    game_state = await emulator.get_game_state()
    if destination.value > MapId.SAFFRON_CITY.value:
        raise FlyError("Fly only accepts a town or city map ID.")
    if Badge.THUNDERBADGE not in game_state.player.badges or game_state.map.tileset not in {
        Tileset.OVERWORLD,
        Tileset.PLATEAU,
    }:
        raise FlyError("Fly is not available here.")
    pokemon_index = next(
        (
            index
            for index, pokemon in enumerate(game_state.party)
            if any(move.name == "FLY" for move in pokemon.moves)
        ),
        None,
    )
    if pokemon_index is None:
        raise FlyError("No party Pokemon knows Fly.")
    await _open_fly_map(emulator, pokemon_index)
    await _select_destination(emulator, destination)
    arrived = await emulator.get_game_state()
    if arrived.map.id != destination:
        raise FlyError(f"The flight ended on {arrived.map.id.name} instead.")
    return f"I flew to {destination.name}."


async def _open_fly_map(emulator: Emulator, pokemon_index: int) -> None:
    """Select Fly from the party action menu."""
    await emulator.press_button(Button.START)
    game_state = await emulator.get_game_state()
    if "POKéMON" not in game_state.screen.text:
        raise FlyError("The START menu did not open.")
    await move_cursor(emulator, game_state.screen.menu_item_index, 1)
    await emulator.press_button(Button.A)
    game_state = await emulator.get_game_state()
    if "Choose a POKéMON." not in game_state.screen.text:
        raise FlyError("The party menu did not open.")
    await move_cursor(emulator, game_state.screen.menu_item_index, pokemon_index)
    await emulator.press_button(Button.A)

    for _ in range(9):
        if "▶FLY" in (await emulator.get_game_state()).screen.text:
            await emulator.press_button(Button.A)
            return
        await emulator.press_button(Button.DOWN)
    raise FlyError("Fly was not in the selected Pokemon's action menu.")


async def _select_destination(emulator: Emulator, destination: MapId) -> None:
    """Select only a destination actually displayed by the game's Fly picker."""
    for _ in range(MapId.SAFFRON_CITY.value + 1):
        screen = (await emulator.get_game_state()).screen
        if destination.name.replace("_", " ") in "".join(screen.decoded_tiles[0]):
            await emulator.press_button(Button.A)
            return
        await emulator.press_button(Button.UP)
    raise FlyError(f"{destination.name} is not available in the Fly destination menu.")


async def _leave_menus(emulator: Emulator) -> None:
    """Back out of a failed selection when a menu is still open."""
    for _ in range(3):
        _, boundary = await emulator.get_game_state_with_control_boundary()
        if boundary == ControlBoundary.OVERWORLD_READY:
            return
        await emulator.press_button(Button.B)
