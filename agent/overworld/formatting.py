"""Model-facing formatting for the explored overworld map."""

from itertools import groupby
from typing import TYPE_CHECKING

import numpy as np

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y
from common.enums import AsciiTile, BlockedDirection, FacingDirection, MapId, WarpActivation
from common.schemas import Coords

if TYPE_CHECKING:
    from collections.abc import Mapping

    from emulator.game_state import GameState
    from emulator.parsers.sign import Sign
    from emulator.parsers.sprite import Sprite
    from emulator.parsers.warp import Warp
    from emulator.schemas import AsciiScreenWithEntities
    from overworld_map.schemas import OverworldMap

_ALWAYS_VISIBLE_TILES = {
    AsciiTile.UNSEEN,
    AsciiTile.WALL,
    AsciiTile.WATER,
    AsciiTile.GRASS,
    AsciiTile.FREE,
    AsciiTile.PLAYER,
    AsciiTile.SPRITE,
    AsciiTile.WARP,
    AsciiTile.PIKACHU,
    AsciiTile.SIGN,
}


def format_explored_percentage(current_map: OverworldMap) -> str:
    """Format the portion of the map that has been explored."""
    explored = np.mean(current_map.ascii_tiles_ndarray != AsciiTile.UNSEEN)
    return f"{explored:.0%}"


def _format_overworld_sprite(sprite: Sprite, map_id: MapId) -> str:
    """Format a known overworld sprite for the agent."""
    output = (
        f"sprite_{map_id}_{sprite.index} at {sprite.coords}."
        f' This sprite is labeled "{sprite.label}".'
    )
    if sprite.moves_randomly:
        output += (
            " Warning: This sprite wanders randomly around the map. Your reactions are too slow"
            " to catch it. Sprites like this are not worth interacting with."
        )
    return output


def _format_overworld_sign(sign: Sign, map_id: MapId) -> str:
    """Format a known overworld sign for the agent."""
    return f"sign_{map_id}_{sign.index} at {sign.coords}."


def _format_overworld_warp(
    warp: Warp,
    map_id: MapId,
    known_map_ids: frozenset[MapId],
    player_coords: Coords,
) -> str:
    """Format a known overworld warp for the agent."""
    if warp.destination in known_map_ids or warp.destination in {MapId.OUTSIDE, MapId.UNKNOWN}:
        destination = warp.destination.name
        if warp.destination_coords is not None:
            destination += f" at {warp.destination_coords}"
        destination_text = f"This warp leads to {destination}."
    else:
        destination_text = (
            "You have not been to this warp's destination yet. Visiting it will add a new "
            " building/floor/location to your memory. It might be a good candidate for"
            " exploration if it is accessible."
        )
    return (
        f"warp_{map_id}_{warp.index} at {warp.coords}. {destination_text}"
        f" {_get_warp_description(warp, player_coords)}"
    )


def _get_warp_description(warp: Warp, player_coords: Coords) -> str:
    """Format instructions for entering a warp."""
    if warp.activation == WarpActivation.STEP_ON:
        if player_coords == warp.coords:
            return "Walk off this coordinate, then step back onto it to activate the warp."
        return "Step onto this coordinate to activate the warp."
    return (
        f"Stand on this coordinate and press {warp.activation.value} to activate the warp, even"
        " if that direction appears blocked."
    )


def format_legend(
    current_map: OverworldMap,
    legend: Mapping[AsciiTile, str],
) -> str:
    """Format the legend for the tile types present on the map."""
    tiles = {
        AsciiTile(tile) for row in current_map.ascii_tiles for tile in row
    } | _ALWAYS_VISIBLE_TILES
    return "\n".join(f'- "{tile}": {legend[tile]}' for tile in AsciiTile if tile in tiles)


def get_facing_tile_notes(game_state: GameState) -> tuple[str, Coords]:
    """Get the tile and map coordinates in front of the player."""
    offset_map = {
        FacingDirection.UP: Coords(row=-1, col=0),
        FacingDirection.DOWN: Coords(row=1, col=0),
        FacingDirection.LEFT: Coords(row=0, col=-1),
        FacingDirection.RIGHT: Coords(row=0, col=1),
    }
    offset = offset_map[game_state.player.direction]
    screen_coords = Coords(row=PLAYER_OFFSET_Y, col=PLAYER_OFFSET_X) + offset
    map_coords = game_state.player.coords + offset
    # We need to check the screen for adjacency because the tile may be on the next map.
    tile = game_state.get_ascii_screen().screen[screen_coords.row][screen_coords.col]
    return tile, map_coords


def get_tile_notes(
    direction: BlockedDirection,
    screen: AsciiScreenWithEntities,
) -> tuple[str, str]:
    """Get an adjacent tile and any elevation-blockage note."""
    text = ", but your movement in this direction is blocked by an elevation difference."
    row_col_map = {
        BlockedDirection.UP: (PLAYER_OFFSET_Y - 1, PLAYER_OFFSET_X),
        BlockedDirection.DOWN: (PLAYER_OFFSET_Y + 1, PLAYER_OFFSET_X),
        BlockedDirection.LEFT: (PLAYER_OFFSET_Y, PLAYER_OFFSET_X - 1),
        BlockedDirection.RIGHT: (PLAYER_OFFSET_Y, PLAYER_OFFSET_X + 1),
    }
    row, col = row_col_map[direction]

    tile = screen.screen[row][col]
    player_coords = Coords(row=PLAYER_OFFSET_Y, col=PLAYER_OFFSET_X)
    blockage = screen.blockages.get(player_coords)
    blocked_text = text if blockage and blockage & direction else ""
    return tile, blocked_text


def format_sprite_notes(current_map: OverworldMap) -> str:
    """Format known sprites in index order."""
    output = ""
    if np.isin(AsciiTile.PC_TILE, current_map.ascii_tiles_ndarray):
        # This is a bit of a hack, but the model really struggles to find the PC otherwise.
        location = np.argwhere(current_map.ascii_tiles_ndarray == AsciiTile.PC_TILE)[0]
        output += (
            f"- There is a PC at {Coords(row=int(location[0]), col=int(location[1]))}. It can only"
            " be interacted with from below.\n"
        )
    elif not current_map.known_sprites:
        return "No sprites discovered."
    output += "\n".join(
        f"- {_format_overworld_sprite(sprite, current_map.id)}"
        for _, sprite in sorted(current_map.known_sprites.items())
    )
    return output.strip()


def format_warp_notes(current_map: OverworldMap, player_coords: Coords) -> str:
    """Format known warps in index order."""
    if not current_map.known_warps:
        return "No warp tiles discovered."
    return "\n".join(
        "- "
        + _format_overworld_warp(
            warp,
            current_map.id,
            current_map.known_map_ids,
            player_coords,
        )
        for _, warp in sorted(current_map.known_warps.items())
    )


def format_sign_notes(current_map: OverworldMap) -> str:
    """Format known signs in index order."""
    if not current_map.known_signs:
        return "No signs discovered."
    return "\n".join(
        f"- {_format_overworld_sign(sign, current_map.id)}"
        for _, sign in sorted(current_map.known_signs.items())
    )


def format_connection_notes(current_map: OverworldMap) -> str:
    """Format direct map connections and navigation guidance."""
    if (
        not current_map.north_connection
        and not current_map.south_connection
        and not current_map.east_connection
        and not current_map.west_connection
    ):
        return (
            "There are no direct connections to other maps on this map. The only way to leave"
            " this map is via warp tiles."
        )
    output = ""
    for direction, connection in [
        ("NORTH", current_map.north_connection),
        ("SOUTH", current_map.south_connection),
        ("EAST", current_map.east_connection),
        ("WEST", current_map.west_connection),
    ]:
        if connection is not None:
            output += f"- The map to the {direction} is {connection.destination_map.name}.\n"
        else:
            output += f"- There is no map connection to the {direction}.\n"
    output += (
        "Important: The fact that you are aware of a map connection does not necessarily mean"
        " that you can access it. If the navigation tool is unable to find a valid path to a"
        " given map connection, it means that you cannot access it from your current position."
        " You either need to explore more of the current map to find it, or you must get to"
        " another part of the current map to access it via an intermediate map (e.g. through"
        " a building or cave)."
    )
    return output.strip()


def format_coordinates_grid(coordinates: list[Coords], map_data: OverworldMap) -> str:
    """Format coordinates and their tile types as a grid."""
    if not coordinates:
        return ""

    coordinates = sorted(coordinates, key=lambda coord: (coord.row, coord.col))
    rows = []
    for _, row_coords in groupby(coordinates, key=lambda coord: coord.row):
        row_str = ", ".join(
            f"({coord.row}, {coord.col}, {map_data.ascii_tiles[coord.row][coord.col]})"
            for coord in row_coords
        )
        rows.append(row_str)
    return "\n".join(rows)


def format_exploration_candidates(
    candidates: list[Coords],
    map_data: OverworldMap,
) -> str:
    """Format exploration candidates for the overworld agent."""
    if not candidates:
        return "No exploration candidates found."
    return format_coordinates_grid(candidates, map_data)


def format_map_boundary_tiles(
    boundary_tiles: dict[FacingDirection, list[Coords]],
    map_data: OverworldMap,
) -> str:
    """Format accessible map boundaries for the overworld agent."""
    output = []
    map_connections = {
        FacingDirection.UP: ("NORTH", map_data.north_connection),
        FacingDirection.DOWN: ("SOUTH", map_data.south_connection),
        FacingDirection.RIGHT: ("EAST", map_data.east_connection),
        FacingDirection.LEFT: ("WEST", map_data.west_connection),
    }

    for facing_dir, (cardinal_dir, connection) in map_connections.items():
        if connection is not None and boundary_tiles[facing_dir]:
            coord_str = ", ".join(str(coord) for coord in boundary_tiles[facing_dir])
            output.append(
                f"The {connection.destination_map.name} map boundary at the far {cardinal_dir}"
                f" of the current map is accessible from {coord_str}.",
            )
        elif connection is not None:
            output.append(
                "You have not yet discovered a valid path to the"
                f" {connection.destination_map.name} map boundary at the far {cardinal_dir} of the"
                f" current map. You can likely find it either by visiting more exploration"
                f" candidates, or perhaps by getting to a new part of the current map via an"
                f" intermediate map (e.g. through a building or cave).",
            )

    return "\n".join(output)
