"""Prompts for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from agent.formatting.game_state import (
    format_inventory_info,
    format_party_info,
    format_pc_info,
    format_player_info,
)
from agent.formatting.memory import format_goals, format_rolling_memory
from agent.overworld import formatting
from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from common.enums import AsciiTile, BlockedDirection

if TYPE_CHECKING:
    from agent.context import AgentContext
    from agent.overworld.map_view import CurrentMapView
    from emulator.game_state import GameState

_STALE_GOAL_ITERATIONS = 100

OVERWORLD_MAP_PROMPT = f"""
<map_info>
Map name: {{map_name}}
<ascii_screen>
{{ascii_screen}}
</ascii_screen>
<current_map_region top_row="{{region_top}}" left_column="{{region_left}}">
{{ascii_map}}
</current_map_region>
<legend>
{{legend}}
</legend>

The complete map's global coordinates in row-column order start at (0, 0) in its top left corner. Rows increase from top to bottom, and columns increase from left to right.

The current map region is a rectangular crop enclosing the area currently navigable from your position, its bordering terrain, and any sprites the game permits you to interact with across a counter. Its first displayed tile is global coordinate ({{region_top}}, {{region_left}}), as recorded in the tag above; displayed rows and columns continue from there without renumbering the underlying coordinates. Walls are shown throughout the rectangle so its physical shape remains clear. "{AsciiTile.OUTSIDE_REGION}" marks every other coordinate inside the rectangle that is outside your current navigable region. Do not target those coordinates directly. Previously remembered coordinates remain valid, and coordinates never change when regions expand, merge, or are entered from another location.

A single map may contain multiple disconnected areas. The displayed current map region is only the area currently reachable from your position without changing maps, based on the terrain revealed so far. Reaching another area of the same map may require leaving through a warp or map boundary and re-entering that map elsewhere.

Coordinates are scoped to their named map. Identical coordinates on different maps or floors are different locations.

<screen_position>
The ASCII screen is always ({SCREEN_HEIGHT}x{SCREEN_WIDTH}) blocks in size, and is always centered such that you are in position ({PLAYER_OFFSET_Y}, {PLAYER_OFFSET_X}) in screen coordinates (not map coordinates). It corresponds 1:1 with the screenshot provided to you above. Note that the screen can extend outside the boundaries of the map (i.e. when the screen boundary rows or columns are negative or exceed the map size).

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

The following discovered sprites are reachable from your current region, either directly or across a counter. Interacting with newly reachable stationary sprites that have no recorded interaction should be a high priority during exploration. Strongly prefer interacting with them before continuing to explore, unless you have a specific reason to pursue another objective. Once an interaction has been recorded, do not repeat it without a specific reason.
<known_sprites>
{{known_sprites}}
</known_sprites>

The following discovered warp tiles are in your current region:
<known_warps>
{{known_warps}}
</known_warps>

The following previously traversed connections are elsewhere on the same map, outside your current connected component. They are informational only: navigation cannot target them from your current component. Use check_connection on a reachable connection, and then on returned connections, to trace known connectivity that may lead to them.
<known_connections_outside_current_component>
{{known_connections_outside_current_component}}
</known_connections_outside_current_component>

The following discovered signs are in your current region. These often only provide flavour text, but could give a useful tip.
<known_signs>
{{known_signs}}
</known_signs>

The following discovered objects are in your current region. These are usually PCs, but can be buttons or switches.
<known_objects>
{{known_objects}}
</known_objects>

Navigation tips:
- You should explore as much of the map as possible, as it may be hiding important sprites, objects, or warp tiles. Exploration is not only a matter of revealing tiles; interact with what you discover along the way. Tiles are considered explored once they are on screen, so move towards unseen territory when you are stuck or unsure how to proceed.
- The orientation of the map and screen is always fixed, regardless of the direction that you are facing.
- Do not use the action button on a warp.
- To interact with a sprite normally, move to an adjacent tile, face it, and press the action button. Do not attempt to move onto the sprite's tile. You cannot walk on or through sprites (except for Pikachu, as described above).
- Some sprite notes provide an exact reachable position for interacting across a counter. In that case, navigate to that position instead of next to the sprite, face the sprite across the "{AsciiTile.COUNTER}" tile, and press the action button.
- Note that some sprites move around, so their position may change between screenshots. Do not let this confuse you. The information that you have in the <known_sprites> section is the most accurate information available to you since it comes straight from the game's memory at this moment in time.

The current ASCII screen is derived from current game memory, while the current map region combines those observations over time. Prefer the ASCII information for tile and coordinate reasoning, and use the screenshot as supplemental visual context.
</map_info>
""".strip()

LEGEND_MAP = {
    AsciiTile.OUTSIDE_REGION: "A non-wall coordinate outside your current navigable region. It may be unexplored or reachable only from somewhere else, so do not target it directly.",
    AsciiTile.UNSEEN: "Tiles that you have not yet explored. Move toward these tiles to reveal them.",
    AsciiTile.WALL: "A barrier (usually a wall or an object) that you cannot pass through.",
    AsciiTile.COUNTER: "A counter that you cannot cross. A listed sprite on its far side can be interacted with only from the exact reachable position stated in that sprite's note.",
    AsciiTile.WATER: "Water.",
    AsciiTile.GRASS: "Tall grass, where wild Pokemon can be found.",
    AsciiTile.LEDGE_DOWN: "A ledge that you can jump down from above. These tiles are only passable if you approach them from above and walk downwards.",
    AsciiTile.LEDGE_LEFT: "A ledge that you can jump over from right to left. These tiles are only passable if you approach them from the right and walk leftwards.",
    AsciiTile.LEDGE_RIGHT: "A ledge that you can jump over from left to right. These tiles are only passable if you approach them from the left and walk rightwards.",
    AsciiTile.FREE: "A walkable tile with nothing noteworthy in it.",
    AsciiTile.PLAYER: "Your current location.",
    AsciiTile.SPRITE: "A sprite. Normally, you interact with it from an adjacent tile; if its note gives an exact interaction position, use that instead. This could be an NPC, an item you can pick up, or some other interactable entity. You cannot walk through sprites, nor can you stand on top of them.",
    AsciiTile.WARP: "A tile that can warp you to a different location. In the screenshot view, these are shown as doors, doormats, staircases, or teleporters.",
    AsciiTile.CUT_TREE: "A tree that can be cut down.",
    AsciiTile.BOULDER_HOLE: "A hole in the ground that you can fall through by standing on it. You can also push boulders into these holes to drop them to the floor below.",
    AsciiTile.PRESSURE_PLATE: "A pressure plate that you can activate by pushing a boulder onto it.",
    AsciiTile.OBJECT: "A discovered stationary object. Its note gives the reachable position and direction needed to interact with it.",
    AsciiTile.PIKACHU: "Your companion Pikachu that follows you around. Unlike other sprites, you can walk through Pikachu, which will cause it to switch places with you. You can speak to Pikachu like any other sprite, but doing so only provides flavour text.",
    AsciiTile.SIGN: "An object that you can interact with to read something. Usually a signpost, but could be a TV, radio, or other object. The main distinction between signs and sprites is that signs are static. They will never move, and their text will never change. Signs are usually interacted with from below, and cannot be walked through.",
    AsciiTile.SPINNER_UP: "A spinner tile that moves you upwards.",
    AsciiTile.SPINNER_DOWN: "A spinner tile that moves you downwards.",
    AsciiTile.SPINNER_LEFT: "A spinner tile that moves you leftwards.",
    AsciiTile.SPINNER_RIGHT: "A spinner tile that moves you rightwards.",
    AsciiTile.SPINNER_STOP: "The tile that stops your spinner movement.",
}

OVERWORLD_DECISION_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text; any dialog from any previous action has already been completed. The screenshot provided above shows the current rendered game screen. After each tool call, its returned screenshot and result are the freshest state and supersede earlier observations.

{state}

The first Pokemon in the party is the lead and will usually receive more battle experience than the rest. If one or two party members are pulling ahead, consider changing the lead to develop the rest of the team. This does not mean every party member needs to be the same level.

Regularly reflect on what you are trying to accomplish and use set_goal to keep your goals useful and current.
{goal_warning}

The following accessible coordinates are adjacent to unseen terrain on the current map. Fully revealing the current map is a high priority. In general, handle newly reachable unvisited stationary sprites before continuing to reveal unseen terrain, but use judgment when a specific objective should take precedence. Exploring these candidates should generally be prioritized before leaving the map, backtracking, or pursuing objectives elsewhere (unless you have a specific other goal in mind or need to heal, of course).
<exploration_candidates>
{exploration_candidates}
</exploration_candidates>

The following section lists only connected-map boundaries reachable from your current region. Boundaries in other regions of the same larger map are omitted.
<map_boundaries>
{map_boundaries}
</map_boundaries>

Use navigation for ordinary movement within the current map. Use press_buttons for direct interactions, changing direction, or sending the final directional input needed to cross a map boundary or warp. Prefer a specialized tool whenever it directly matches the action you want to take.

Briefly explain your reasoning in first person as ordinary response text, then use exactly one available tool to act. Be sure to consider all the tools at your disposal. Every response must include one tool call. A fresh observation will be returned after each tool executes.

{biking_warning}
""".strip()


def _format_overworld_map(map_view: CurrentMapView, game_state: GameState) -> str:
    """Build the explored-map portion of the overworld prompt."""
    current_map = map_view.overworld_map
    screen = game_state.get_ascii_screen()
    known_warps, external_connections = formatting.format_connection_sections(
        map_view,
        game_state,
    )
    facing_tile, facing_tile_coords = formatting.get_facing_tile_notes(game_state)
    tile_above, blocked_above = formatting.get_tile_notes(BlockedDirection.UP, screen)
    tile_below, blocked_below = formatting.get_tile_notes(BlockedDirection.DOWN, screen)
    tile_left, blocked_left = formatting.get_tile_notes(BlockedDirection.LEFT, screen)
    tile_right, blocked_right = formatting.get_tile_notes(BlockedDirection.RIGHT, screen)
    return OVERWORLD_MAP_PROMPT.format(
        map_name=current_map.id.name,
        ascii_map="\n".join("".join(row) for row in map_view.display_tiles),
        legend=formatting.format_legend(map_view, LEGEND_MAP),
        region_top=map_view.display_origin.row,
        region_left=map_view.display_origin.col,
        known_sprites=formatting.format_sprite_notes(map_view, game_state),
        known_warps=known_warps,
        known_connections_outside_current_component=external_connections,
        known_signs=formatting.format_sign_notes(map_view, game_state),
        known_objects=formatting.format_object_notes(map_view, game_state),
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
        connections=formatting.format_connection_notes(map_view),
    )


def build_overworld_decision_prompt(
    context: AgentContext,
    map_view: CurrentMapView,
    game_state: GameState,
) -> str:
    """Build the initial prompt for one overworld-agent run."""
    current_map = map_view.overworld_map
    if game_state.player.is_biking:
        unavailable = "Navigation data is unavailable while riding a bike."
        exploration_candidates = unavailable
        map_boundaries = unavailable
        biking_warning = "You have lost access to the navigation tool because you are riding a bike. If you would like to use the navigation tool, you must first dismount your bike. If you are unable to dismount your bike because you are on Cycling Road, then you must use the button tool to move around the map."
    else:
        exploration_candidates = formatting.format_exploration_candidates(
            map_view.exploration_candidates,
            current_map,
        )
        map_boundaries = formatting.format_map_boundary_tiles(
            map_view.boundary_tiles,
            current_map,
        )
        biking_warning = ""

    sections = (
        format_rolling_memory(context.state.rolling_memory),
        format_goals(context.state.goals),
        _format_overworld_map(map_view, game_state),
        format_player_info(game_state),
        format_party_info(game_state),
        format_inventory_info(game_state),
        format_pc_info(game_state),
    )
    goal_warning = ""
    if context.state.goals.goals and all(
        context.state.iteration - goal.updated_at_iteration > _STALE_GOAL_ITERATIONS
        for goal in context.state.goals.goals
    ):
        goal_warning = (
            "Your goals have not been updated in over 100 iterations. You may want to review them."
        )
    return OVERWORLD_DECISION_PROMPT.format(
        state="\n\n".join(section for section in sections if section),
        exploration_candidates=exploration_candidates,
        map_boundaries=map_boundaries,
        biking_warning=biking_warning,
        goal_warning=goal_warning,
    )
