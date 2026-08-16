"""Model-facing formatting for the explored overworld map."""

from itertools import groupby
from typing import TYPE_CHECKING

import numpy as np

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y
from common.enums import AsciiTile, BlockedDirection, FacingDirection, MapId, WarpActivation
from common.schemas import Coords

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from agent.overworld.map_view import CurrentMapView
    from emulator.game_state import GameState
    from emulator.parsers.sign import Sign
    from emulator.parsers.sprite import Sprite
    from emulator.parsers.warp import Warp
    from emulator.schemas import AsciiScreenWithEntities
    from overworld_map.schemas import MapEntityInteractionMemory, OverworldMap

_ALWAYS_VISIBLE_TILES = {
    AsciiTile.OUTSIDE_REGION,
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

# These buildings are visually identifiable from their exterior before the player enters them, so
# revealing their destination does not give the agent information unavailable on the game screen.
_VISIBLE_UNVISITED_DESTINATIONS = frozenset(
    {
        MapId.VIRIDIAN_POKECENTER,
        MapId.PEWTER_POKECENTER,
        MapId.CERULEAN_POKECENTER,
        MapId.MT_MOON_POKECENTER,
        MapId.ROCK_TUNNEL_POKECENTER,
        MapId.VERMILION_POKECENTER,
        MapId.CELADON_POKECENTER,
        MapId.LAVENDER_POKECENTER,
        MapId.FUCHSIA_POKECENTER,
        MapId.CINNABAR_POKECENTER,
        MapId.SAFFRON_POKECENTER,
        MapId.VIRIDIAN_GYM,
        MapId.PEWTER_GYM,
        MapId.CERULEAN_GYM,
        MapId.VERMILION_GYM,
        MapId.CELADON_GYM,
        MapId.FUCHSIA_GYM,
        MapId.CINNABAR_GYM,
        MapId.SAFFRON_GYM,
        MapId.VIRIDIAN_MART,
        MapId.PEWTER_MART,
        MapId.CERULEAN_MART,
        MapId.VERMILION_MART,
        MapId.CELADON_MART_1F,
        MapId.LAVENDER_MART,
        MapId.FUCHSIA_MART,
        MapId.CINNABAR_MART,
        MapId.SAFFRON_MART,
    }
)


def _format_overworld_sprite(
    sprite: Sprite,
    map_id: MapId,
    counter_positions: tuple[Coords, ...],
    interaction: MapEntityInteractionMemory | None,
) -> str:
    """Format a known overworld sprite for the agent."""
    output = (
        f"sprite_{map_id}_{sprite.index} at {sprite.coords}."
        f' This sprite is labeled "{sprite.label}".'
    )
    if interaction is None:
        output += " You have not interacted with this sprite yet."
    else:
        output += f' Last interaction (iteration {interaction.iteration}): "{interaction.text}"'
    if counter_positions:
        positions = ", ".join(str(position) for position in counter_positions)
        output += (
            f" It can be interacted with across a counter from {positions}; stand there,"
            " face the sprite, and press the action button."
        )
    if sprite.moves_randomly:
        output += (
            " Warning: This sprite wanders randomly around the map. Your reactions are too slow"
            " to catch it. Sprites like this are not worth interacting with."
        )
    return output


def _format_overworld_sign(
    sign: Sign,
    map_id: MapId,
    interaction: MapEntityInteractionMemory | None,
) -> str:
    """Format a known overworld sign for the agent."""
    output = f"sign_{map_id}_{sign.index} at {sign.coords}."
    if interaction is None:
        return output + " You have not interacted with this sign yet."
    return output + f' Last interaction (iteration {interaction.iteration}): "{interaction.text}"'


def _format_overworld_warp(
    warp: Warp,
    map_id: MapId,
    known_map_ids: frozenset[MapId],
    player_coords: Coords,
) -> str:
    """Format a known overworld warp for the agent."""
    if (
        warp.destination in known_map_ids
        or warp.destination in {MapId.OUTSIDE, MapId.UNKNOWN}
        or warp.destination in _VISIBLE_UNVISITED_DESTINATIONS
    ):
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
            return (
                "You are currently standing on this warp, so it is inactive. It activates only"
                " when entered from another tile. Re-enter it only when you intend to travel to"
                " the destination described above."
            )
        return "Step onto this coordinate to activate the warp."
    return (
        f"Stand on this coordinate and press {warp.activation.value} to activate the warp, even"
        " if that direction appears blocked."
    )


def format_legend(
    map_view: CurrentMapView,
    legend: Mapping[AsciiTile, str],
) -> str:
    """Format the legend for the tile types present on the map."""
    tiles = {
        AsciiTile(tile) for row in map_view.display_tiles for tile in row
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


def format_sprite_notes(map_view: CurrentMapView, game_state: GameState) -> str:
    """Format known sprites in index order."""
    current_map = map_view.overworld_map
    output = ""
    sprites = [
        game_state.sprites[entity_id]
        for entity_id in sorted(current_map.known_sprite_ids)
        if entity_id in game_state.sprites
        and game_state.sprites[entity_id].coords in map_view.visible_coords
    ]
    pc_locations = np.argwhere(current_map.terrain_ndarray == AsciiTile.PC_TILE)
    if len(pc_locations) > 0:
        # This is a bit of a hack, but the model really struggles to find the PC otherwise.
        location = Coords(row=int(pc_locations[0][0]), col=int(pc_locations[0][1]))
        if location in map_view.visible_coords:
            output += f"- There is a PC at {location}. It can only be interacted with from below.\n"
    if not output and not sprites:
        return "No sprites discovered."
    output += "\n".join(
        "- "
        + _format_overworld_sprite(
            sprite,
            current_map.id,
            map_view.counter_interactions.get(sprite.index, ()),
            current_map.sprite_interactions.get(sprite.index),
        )
        for sprite in sprites
    )
    return output.strip()


def format_warp_notes(map_view: CurrentMapView, game_state: GameState) -> str:
    """Format known warps in index order."""
    current_map = map_view.overworld_map
    warps = [
        game_state.warps[entity_id]
        for entity_id in sorted(current_map.known_warp_ids)
        if entity_id in game_state.warps
        and game_state.warps[entity_id].coords in map_view.visible_coords
    ]
    if not warps:
        return "No warp tiles discovered."
    return "\n".join(
        "- "
        + _format_overworld_warp(
            warp,
            current_map.id,
            current_map.known_map_ids,
            game_state.player.coords,
        )
        for warp in warps
    )


def format_sign_notes(map_view: CurrentMapView, game_state: GameState) -> str:
    """Format known signs in index order."""
    current_map = map_view.overworld_map
    signs = [
        game_state.signs[entity_id]
        for entity_id in sorted(current_map.known_sign_ids)
        if entity_id in game_state.signs
        and game_state.signs[entity_id].coords in map_view.visible_coords
    ]
    if not signs:
        return "No signs discovered."
    return "\n".join(
        "- "
        + _format_overworld_sign(
            sign,
            current_map.id,
            current_map.sign_interactions.get(sign.index),
        )
        for sign in signs
    )


def format_connection_notes(map_view: CurrentMapView) -> str:
    """Format direct map connections reachable from the current region."""
    current_map = map_view.overworld_map
    connections = [
        ("NORTH", FacingDirection.UP, current_map.north_connection),
        ("SOUTH", FacingDirection.DOWN, current_map.south_connection),
        ("EAST", FacingDirection.RIGHT, current_map.east_connection),
        ("WEST", FacingDirection.LEFT, current_map.west_connection),
    ]
    reachable_connections = [
        (direction, connection)
        for direction, facing, connection in connections
        if connection is not None and map_view.boundary_tiles[facing]
    ]
    if not reachable_connections:
        return (
            "There are no direct connections to other maps reachable from your current region."
            " Leave it through a reachable warp or expand it by exploring unseen terrain."
        )
    return "\n".join(
        f"- The map to the {direction} is {connection.destination_map.name}."
        for direction, connection in reachable_connections
    )


def format_coordinates_grid(
    coordinates: Sequence[Coords],
    map_data: OverworldMap,
) -> str:
    """Format coordinates and their tile types as a grid."""
    if not coordinates:
        return ""

    coordinates = sorted(coordinates, key=lambda coord: (coord.row, coord.col))
    rows = []
    for _, row_coords in groupby(coordinates, key=lambda coord: coord.row):
        row_str = ", ".join(
            f"({coord.row}, {coord.col}, {map_data.terrain[coord.row][coord.col]})"
            for coord in row_coords
        )
        rows.append(row_str)
    return "\n".join(rows)


def format_exploration_candidates(
    candidates: Sequence[Coords],
    map_data: OverworldMap,
) -> str:
    """Format exploration candidates for the overworld agent."""
    if not candidates:
        return "No exploration candidates found."
    return format_coordinates_grid(candidates, map_data)


def format_map_boundary_tiles(
    boundary_tiles: Mapping[FacingDirection, Sequence[Coords]],
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
    return "\n".join(output) or "No connected-map boundary is reachable from this region."
