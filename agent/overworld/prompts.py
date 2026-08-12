"""Prompts for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from agent.formatting.game_state import format_party_info, format_pc_info, format_player_info
from agent.formatting.memory import format_goals, format_rolling_memory
from agent.overworld import formatting
from agent.overworld.tools.navigate import utils
from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from common.enums import AsciiTile, BlockedDirection
from overworld_map.views import get_current_map_tiles

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap

OVERWORLD_MAP_PROMPT = f"""
<map_info>
Map name: {{map_name}}
<ascii_screen>
{{ascii_screen}}
</ascii_screen>
<whole_map>
{{ascii_map}}
</whole_map>
You have explored {{explored_percentage}} of this map.
<legend>
{{legend}}
</legend>

The map coordinates in row-column order start at (0, 0) in the top left corner. The rows increase from top to bottom, and the columns increase from left to right. The full size of the current map in row-column order is {{height}}x{{width}} blocks.

<screen_position>
The ASCII screen is always ({SCREEN_HEIGHT}x{SCREEN_WIDTH}) blocks in size, and is always centered such that you are in position ({PLAYER_OFFSET_Y}, {PLAYER_OFFSET_X}) in screen coordinates (not map coordinates). It corresponds 1:1 with the screenshot provided to you above. Note that the screen can extend outside the boundaries of the map (i.e. when the screen boundary rows or columns are negative or exceed the map size). This should help you navigate from one map to another.

The top of the screen is currently at row {{screen_top}} in map coordinates.
The bottom of the screen is currently at row {{screen_bottom}} in map coordinates.
The left side of the screen is currently at column {{screen_left}} in map coordinates.
The right side of the screen is currently at column {{screen_right}} in map coordinates.
</screen_position>

<player_position>
You, the player, are at position {{player_coords}} in map coordinates.
The terrain tile beneath you is "{{player_terrain}}".
You are facing {{player_direction}}. The tile you are facing is "{{facing_tile}}" at position {{facing_tile_coords}}.

The tile directly above you is "{{tile_above}}"{{blocked_above}}.
The tile directly below you is "{{tile_below}}"{{blocked_below}}.
The tile directly to the left of you is "{{tile_left}}"{{blocked_left}}.
The tile directly to the right of you is "{{tile_right}}"{{blocked_right}}.
</player_position>

<map_connections>
{{connections}}
</map_connections>

You have discovered the following sprites on the portion of the map that you have revealed so far. Do not make any assumptions about who or what a sprite is before you have interacted with it.
<known_sprites>
{{known_sprites}}
</known_sprites>

You have discovered the following warp tiles on the portion of the map that you have revealed so far:
<known_warps>
{{known_warps}}
</known_warps>

You have discovered the following signs on the portion of the map that you have revealed so far:
<known_signs>
{{known_signs}}
</known_signs>

Navigation tips:
- You should explore as much of the map as possible to reveal unexplored tiles, as they may be hiding important sprites or warp tiles. Tiles are considered explored once they are on screen, so move towards unseen territory when you are stuck or unsure how to proceed.
- The orientation of the map and screen is always fixed, regardless of the direction that you are facing.
- Do not use the action button on a warp.
- To connect from one map to another, you must either use a warp tile, or, *in outdoor maps only*, walk off the edge of the map. In outdoor maps, you will never be able to walk through a wall or barrier for any reason. You have to find where the edge of the map connects to the next map by looking at the ASCII screen.
- If you are indoors, the edges of the map (indicated by a black void in the screenshot) are normally impassable. Move outward at an indoor edge only when a discovered warp's instruction explicitly requires it.
- Pay attention to the "leading to" description in each warp tile. This comes straight from the game's memory and will tell you which map you will be warped to from that tile.
- To interact with a sprite, you need to be directly adjacent to it, face it, and press the action button. The only exception to the direct adjacency rule is in Poke Marts, Pokemon Centers, or gates where you interact with the clerk/nurse/guard respectively from across the counter. In these cases, you must stand two tiles away from the sprite (horizontally or vertically depending on the counter, but not diagonally), face it across the counter (an adjacent "{AsciiTile.WALL}" tile), and press the action button.
- If you want to interact with a sprite, you should move to the tile adjacent to it. Do not attempt to move onto the sprite's tile. You cannot walk on or through sprites (except for Pikachu, as described above).
- Note that some sprites move around, so their position may change between screenshots. Do not let this confuse you. The information that you have in the <known_sprites> section is the most accurate information available to you since it comes straight from the game's memory at this moment in time.
- It is generally not worth interacting with sprites and signs more than once. They usually do not change between interactions.
- Pay attention to the "sprite is labeled" section in each sprite. This will tell you what the sprite is labeled as in the game's memory, and should help you determine what the sprite is.
- Focus on the map when you are trying to navigate within a map. Focus on the screen when you are trying to navigate between maps.

The current ASCII screen is derived from current game memory, while the whole map combines those observations over time. Prefer the ASCII information for tile and coordinate reasoning, and use the screenshot as supplemental visual context.
</map_info>
""".strip()

LEGEND_MAP = {
    AsciiTile.UNSEEN: "Tiles that you have not yet explored. Move toward these tiles to reveal them.",
    AsciiTile.WALL: "A barrier (usually a wall or an object) that you cannot pass through.",
    AsciiTile.WATER: "Water.",
    AsciiTile.GRASS: "Tall grass, where wild Pokemon can be found.",
    AsciiTile.LEDGE_DOWN: "A ledge that you can jump down from above. These tiles are only passable if you approach them from above and walk downwards.",
    AsciiTile.LEDGE_LEFT: "A ledge that you can jump over from right to left. These tiles are only passable if you approach them from the right and walk leftwards.",
    AsciiTile.LEDGE_RIGHT: "A ledge that you can jump over from left to right. These tiles are only passable if you approach them from the left and walk rightwards.",
    AsciiTile.FREE: "A walkable tile with nothing noteworthy in it.",
    AsciiTile.PLAYER: "Your current location.",
    AsciiTile.SPRITE: "A sprite that you can interact with from an adjacent tile. This could be an NPC, an item you can pick up, or some other interactable entity. You cannot walk through sprites, nor can you stand on top of them.",
    AsciiTile.WARP: "A tile that can warp you to a different location. In the screenshot view, these are shown as doors, doormats, staircases, or teleporters.",
    AsciiTile.CUT_TREE: "A tree that can be cut down.",
    AsciiTile.BOULDER_HOLE: "A hole in the ground that you can fall through by standing on it. You can also push boulders into these holes to drop them to the floor below.",
    AsciiTile.PRESSURE_PLATE: "A pressure plate that you can activate by pushing a boulder onto it.",
    AsciiTile.PC_TILE: "The PC in a Pokemon Center. You can swap your party members with boxed Pokemon by interacting with it. The PC can only be interacted with from below.",
    AsciiTile.PIKACHU: "Your companion Pikachu that follows you around. Unlike other sprites, you can walk through Pikachu, which will cause it to switch places with you. You can speak to Pikachu like any other sprite, but doing so only provides flavour text.",
    AsciiTile.SIGN: "An object that you can interact with to read something. Usually a signpost, but could be a TV, radio, or other object. The main distinction between signs and sprites is that signs are static. They will never move, and their text will never change. Signs are usually interacted with from below, and cannot be walked through.",
    AsciiTile.SPINNER_UP: "A spinner tile that moves you upwards.",
    AsciiTile.SPINNER_DOWN: "A spinner tile that moves you downwards.",
    AsciiTile.SPINNER_LEFT: "A spinner tile that moves you leftwards.",
    AsciiTile.SPINNER_RIGHT: "A spinner tile that moves you rightwards.",
    AsciiTile.SPINNER_STOP: "The tile that stops your spinner movement.",
}

OVERWORLD_DECISION_PROMPT = """
You are navigating the overworld. At entry, you are standing still, there is no
onscreen text, and all onscreen animations have concluded. The screenshot
provided above shows the game screen at entry. After each tool call, its
returned screenshot and result are the freshest state and supersede earlier
observations.

{state}

The following accessible coordinates are adjacent to unseen territory on the
current map. They are therefore top candidates for exploration. If the section
below is empty, then you have already explored all of the accessible tiles on
the current map. Navigating towards any of these exploration candidates is the
most efficient way to explore the map.
<exploration_candidates>
{exploration_candidates}
</exploration_candidates>

If there are maps connected to the current map, the following section will
guide you on how to navigate to the boundaries of the current map so that you
can transition to the next map in the next iteration if you choose to do so.
If this section is empty, it means that the current map is not connected to
any other maps and has to be exited via warp tiles.
<map_boundaries>
{map_boundaries}
</map_boundaries>

Your current inventory is listed below:
<inventory_indices>
{inventory_indices}
</inventory_indices>

Use navigation for ordinary movement within the current map. Use press_buttons
for direct interactions, changing direction, or sending the final directional
input needed to cross a map boundary or warp. Prefer a specialized tool
whenever it directly matches the action you want to take.

Briefly explain your reasoning in first person as ordinary response text, then
use exactly one available tool to act. Be sure to consider all the tools at
your disposal. Every response must include one tool call. A fresh observation
will be returned after each tool executes.

{biking_warning}
""".strip()


def _format_overworld_map(current_map: OverworldMap, game_state: GameState) -> str:
    """Build the explored-map portion of the overworld prompt."""
    screen = game_state.get_ascii_screen()
    facing_tile, facing_tile_coords = formatting.get_facing_tile_notes(game_state)
    tile_above, blocked_above = formatting.get_tile_notes(BlockedDirection.UP, screen)
    tile_below, blocked_below = formatting.get_tile_notes(BlockedDirection.DOWN, screen)
    tile_left, blocked_left = formatting.get_tile_notes(BlockedDirection.LEFT, screen)
    tile_right, blocked_right = formatting.get_tile_notes(BlockedDirection.RIGHT, screen)
    current_tiles = get_current_map_tiles(current_map, game_state)
    return OVERWORLD_MAP_PROMPT.format(
        map_name=current_map.id.name,
        ascii_map="\n".join("".join(row) for row in current_tiles),
        legend=formatting.format_legend(current_map, LEGEND_MAP),
        height=current_map.height,
        width=current_map.width,
        known_sprites=formatting.format_sprite_notes(current_map, game_state),
        known_warps=formatting.format_warp_notes(current_map, game_state),
        known_signs=formatting.format_sign_notes(current_map, game_state),
        explored_percentage=formatting.format_explored_percentage(current_map),
        ascii_screen=screen,
        player_coords=game_state.player.coords,
        player_terrain=current_map.terrain[game_state.player.coords.row][
            game_state.player.coords.col
        ],
        player_direction=game_state.player.direction,
        facing_tile=facing_tile,
        facing_tile_coords=facing_tile_coords,
        tile_above=tile_above,
        blocked_above=blocked_above,
        tile_below=tile_below,
        blocked_below=blocked_below,
        tile_left=tile_left,
        blocked_left=blocked_left,
        tile_right=tile_right,
        blocked_right=blocked_right,
        screen_top=game_state.screen.top,
        screen_left=game_state.screen.left,
        screen_bottom=game_state.screen.bottom,
        screen_right=game_state.screen.right,
        connections=formatting.format_connection_notes(current_map),
    )


def build_overworld_decision_prompt(
    context: AgentContext,
    current_map: OverworldMap,
    game_state: GameState,
) -> str:
    """Build the initial prompt for one overworld-agent run."""
    if game_state.player.is_biking:
        unavailable = "Navigation data is unavailable while riding a bike."
        exploration_candidates = unavailable
        map_boundaries = unavailable
        biking_warning = (
            "You have lost access to the navigation tool because you are riding a bike. If you "
            "would like to use the navigation tool, you must first dismount your bike. If you are "
            "unable to dismount your bike because you are on Cycling Road, then you must use the "
            "button tool to move around the map."
        )
    else:
        navigation_tiles = get_current_map_tiles(current_map, game_state)
        accessible = utils.get_accessible_coords(
            game_state.player.coords,
            navigation_tiles,
            current_map.blockages,
            game_state.get_hm_tiles(),
        )
        exploration = utils.get_exploration_candidates(accessible, navigation_tiles)
        boundaries = utils.get_map_boundary_tiles(accessible, current_map)
        exploration_candidates = formatting.format_exploration_candidates(
            exploration,
            current_map,
        )
        map_boundaries = formatting.format_map_boundary_tiles(boundaries, current_map)
        biking_warning = ""

    inventory_indices = "\n".join(
        f"[{index}] {item.name} (x{item.quantity})"
        for index, item in enumerate(game_state.inventory.items)
    )
    sections = (
        format_rolling_memory(context.state.rolling_memory),
        format_goals(context.state.goals),
        _format_overworld_map(current_map, game_state),
        format_player_info(game_state),
        format_party_info(game_state),
        format_pc_info(game_state),
    )
    return OVERWORLD_DECISION_PROMPT.format(
        state="\n\n".join(section for section in sections if section),
        exploration_candidates=exploration_candidates,
        map_boundaries=map_boundaries,
        biking_warning=biking_warning,
        inventory_indices=inventory_indices,
    )
