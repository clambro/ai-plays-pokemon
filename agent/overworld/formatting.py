"""Model-facing formatting for the explored overworld map."""

from itertools import groupby
from typing import TYPE_CHECKING

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y
from common.enums import AsciiTile, BlockedDirection, FacingDirection, MapId, WarpActivation
from common.schemas import Coords

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from agent.overworld.map_view import CurrentMapView, ObjectInteractionPosition
    from emulator.game_state import GameState
    from emulator.parsers.sign import Sign
    from emulator.parsers.sprite import Sprite
    from emulator.parsers.static_object import StaticObject
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
    AsciiTile.OBJECT,
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
        output += " You have not interacted with this sprite yet; it may be worth trying."
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
        return output + " You have not interacted with this sign yet; it may be worth reading."
    return output + f' Last interaction (iteration {interaction.iteration}): "{interaction.text}"'


def _format_overworld_object(
    obj: StaticObject,
    map_id: MapId,
    positions: Sequence[ObjectInteractionPosition],
    interaction: MapEntityInteractionMemory | None,
) -> str:
    """Format a known stationary object for the agent."""
    output = f"object_{map_id}_{obj.index} at {obj.coords}."
    if len(positions) == 1:
        position = positions[0]
        output += (
            f" To interact with it, stand at {position.coords}, face"
            f" {position.direction.value}, and press the action button."
        )
    else:
        choices = "; ".join(
            f"{position.coords} facing {position.direction.value}" for position in positions
        )
        output += (
            f" To interact with it, use one of these positions: {choices}; then press the action"
            " button."
        )
    if interaction is None:
        return output + " You have not interacted with this object yet; it may be worth trying."
    return output + f' Last interaction (iteration {interaction.iteration}): "{interaction.text}"'


def _format_overworld_warp(
    warp: Warp,
    map_id: MapId,
    known_map_ids: frozenset[MapId],
    player_coords: Coords,
    last_interaction_iteration: int | None,
) -> str:
    """Format a known overworld warp for the agent."""
    if warp.destination in {MapId.OUTSIDE, MapId.UNKNOWN}:
        destination_text = "This warp's destination is unresolved."
    elif warp.destination in known_map_ids or warp.destination in _VISIBLE_UNVISITED_DESTINATIONS:
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
    output = (
        f"warp_{map_id}_{warp.index} at {warp.coords}. {destination_text}"
        f" {_get_warp_description(warp, player_coords)}"
    )
    if last_interaction_iteration is not None:
        output += f" Last used at iteration {last_interaction_iteration}."
    else:
        output += " No recorded use."
    return output


def _get_warp_group_last_used_iteration(
    warp: Warp,
    warps: Sequence[Warp],
    usage_iterations: Mapping[int, int],
) -> int | None:
    """Get the newest usage timestamp for one contiguous multi-tile warp."""
    matching_warps = [
        candidate
        for candidate in warps
        if candidate.destination == warp.destination
        and candidate.destination_warp_index == warp.destination_warp_index
        and candidate.destination_coords == warp.destination_coords
        and candidate.activation == warp.activation
    ]
    group_ids = {warp.index}
    pending = [warp]
    while pending:
        current = pending.pop()
        for candidate in matching_warps:
            if candidate.index in group_ids:
                continue
            distance = abs(candidate.coords.row - current.coords.row) + abs(
                candidate.coords.col - current.coords.col
            )
            if distance != 1:
                continue
            group_ids.add(candidate.index)
            pending.append(candidate)

    return max(
        (usage_iterations[index] for index in group_ids if index in usage_iterations),
        default=None,
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
        f"Stand on this coordinate and press {warp.activation.value} twice to activate the warp,"
        " even if that direction appears blocked. The first press turns you if necessary; the"
        " second moves you through the warp."
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
    sprites = [
        game_state.sprites[entity_id]
        for entity_id in sorted(current_map.known_sprite_ids)
        if entity_id in game_state.sprites
        and game_state.sprites[entity_id].coords in map_view.visible_coords
    ]
    if not sprites:
        return "No sprites discovered."
    return "\n".join(
        "- "
        + _format_overworld_sprite(
            sprite,
            current_map.id,
            map_view.counter_interactions.get(sprite.index, ()),
            current_map.sprite_interactions.get(sprite.index),
        )
        for sprite in sprites
    )


def format_warp_notes(
    map_view: CurrentMapView,
    game_state: GameState,
) -> str:
    """Format known warps in index order."""
    current_map = map_view.overworld_map
    known_warps = [
        game_state.warps[entity_id]
        for entity_id in sorted(current_map.known_warp_ids)
        if entity_id in game_state.warps
    ]
    warps = [warp for warp in known_warps if warp.coords in map_view.visible_coords]
    if not warps:
        return "No warp tiles discovered."
    return "\n".join(
        "- "
        + _format_overworld_warp(
            warp,
            current_map.id,
            current_map.known_map_ids,
            game_state.player.coords,
            _get_warp_group_last_used_iteration(
                warp,
                known_warps,
                current_map.warp_usage_iterations,
            ),
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


def format_object_notes(map_view: CurrentMapView, game_state: GameState) -> str:
    """Format known stationary objects in index order."""
    current_map = map_view.overworld_map
    objects = [
        game_state.objects[entity_id]
        for entity_id in sorted(current_map.known_object_ids)
        if entity_id in game_state.objects
        and game_state.objects[entity_id].coords in map_view.visible_coords
        and entity_id in map_view.object_interaction_positions
    ]
    if not objects:
        return "No objects discovered."
    return "\n".join(
        "- "
        + _format_overworld_object(
            obj,
            current_map.id,
            map_view.object_interaction_positions[obj.index],
            current_map.object_interactions.get(obj.index),
        )
        for obj in objects
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
        return "No unexplored terrain candidates found."
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
