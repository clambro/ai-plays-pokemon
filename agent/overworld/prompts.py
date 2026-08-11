"""Prompts for the Pydantic AI overworld agent."""

from itertools import groupby
from typing import TYPE_CHECKING

from agent.overworld.tools.navigate import utils
from common.enums import FacingDirection

if TYPE_CHECKING:
    from agent.context import AgentContext
    from common.schemas import Coords
    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap

OVERWORLD_DECISION_PROMPT = """
You are navigating the overworld. At entry, you are standing still, there is no
onscreen text, and all onscreen animations have concluded. The screenshot
provided above shows the game screen at entry. After each tool call, its
returned screenshot and result are the freshest state and supersede earlier
observations.

{state}

The following titles already exist in your long-term memory. They are the
documents available to the retrieval tool. Use them both to select relevant
memories and to avoid creating duplicate or near-duplicate documents:
<available_long_term_memory_titles>
{available_long_term_memory_titles}
</available_long_term_memory_titles>

The coordinates in the format (row, col, tile type) that are accessible from
your current position are as follows:
<accessible_coords>
{accessible_coords}
</accessible_coords>

The following coordinates (a subset of the accessible coordinates provided
above) are adjacent to unseen territory on the current map. They are therefore
top candidates for exploration. If the section below is empty, then you have
already explored all of the accessible tiles on the current map. Navigating
towards any of these exploration candidates is the most efficient way to
explore the map.
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

Briefly explain your reasoning in first person as ordinary response text, then
use exactly one available tool to act. Be sure to consider all the tools at
your disposal. Every response must include one tool call. A fresh observation
will be returned after each tool executes.

{biking_warning}
""".strip()


def build_overworld_decision_prompt(
    context: AgentContext,
    current_map: OverworldMap,
    available_long_term_memory_titles: list[str],
    game_state: GameState,
) -> str:
    """Build the initial prompt for one overworld-agent run."""
    if game_state.player.is_biking:
        unavailable = "Navigation data is unavailable while riding a bike."
        accessible_coords = unavailable
        exploration_candidates = unavailable
        map_boundaries = unavailable
        biking_warning = (
            "You have lost access to the navigation tool because you are riding a bike. If you "
            "would like to use the navigation tool, you must first dismount your bike. If you are "
            "unable to dismount your bike because you are on Cycling Road, then you must use the "
            "button tool to move around the map."
        )
    else:
        accessible = utils.get_accessible_coords(
            game_state.player.coords,
            current_map,
            game_state.get_hm_tiles(),
        )
        exploration = utils.get_exploration_candidates(accessible, current_map)
        boundaries = utils.get_map_boundary_tiles(accessible, current_map)
        accessible_coords = _format_coordinates_grid(accessible, current_map)
        exploration_candidates = _format_exploration_candidates(
            exploration,
            current_map,
        )
        map_boundaries = _format_map_boundary_tiles(boundaries, current_map)
        biking_warning = ""

    inventory_indices = "\n".join(
        f"[{index}] {item.name} (x{item.quantity})"
        for index, item in enumerate(game_state.inventory.items)
    )
    return OVERWORLD_DECISION_PROMPT.format(
        state="\n\n".join(
            (
                str(context.state.rolling_memory),
                str(context.state.long_term_memory),
                str(context.state.goals),
                current_map.to_string(game_state),
                game_state.player_info,
            ),
        ),
        available_long_term_memory_titles="\n".join(
            available_long_term_memory_titles,
        ),
        accessible_coords=accessible_coords,
        exploration_candidates=exploration_candidates,
        map_boundaries=map_boundaries,
        biking_warning=biking_warning,
        inventory_indices=inventory_indices,
    )


def _format_coordinates_grid(coordinates: list[Coords], map_data: OverworldMap) -> str:
    """Format coordinates and their tile types as a grid."""
    if not coordinates:
        return ""

    coordinates = sorted(coordinates, key=lambda c: (c.row, c.col))
    rows = []
    for _, row_coords in groupby(coordinates, key=lambda c: c.row):
        row_str = ", ".join(
            f"({c.row}, {c.col}, {map_data.ascii_tiles[c.row][c.col]})" for c in row_coords
        )
        rows.append(row_str)
    return "\n".join(rows)


def _format_exploration_candidates(
    candidates: list[Coords],
    map_data: OverworldMap,
) -> str:
    """Format exploration candidates for LLM consumption."""
    if not candidates:
        return "No exploration candidates found."
    return _format_coordinates_grid(candidates, map_data)


def _format_map_boundary_tiles(
    boundary_tiles: dict[FacingDirection, list[Coords]],
    map_data: OverworldMap,
) -> str:
    """Format accessible map boundaries for LLM consumption."""
    output = []
    map_connections = {
        FacingDirection.UP: ("NORTH", map_data.north_connection),
        FacingDirection.DOWN: ("SOUTH", map_data.south_connection),
        FacingDirection.RIGHT: ("EAST", map_data.east_connection),
        FacingDirection.LEFT: ("WEST", map_data.west_connection),
    }

    for facing_dir, (cardinal_dir, connection) in map_connections.items():
        if connection is not None and boundary_tiles[facing_dir]:
            coord_str = ", ".join(str(c) for c in boundary_tiles[facing_dir])
            output.append(
                f"The {connection.name} map boundary at the far {cardinal_dir} of the current map"
                f" is accessible from {coord_str}.",
            )
        elif connection is not None:
            output.append(
                f"You have not yet discovered a valid path to the {connection.name} map"
                f" boundary at the far {cardinal_dir} of the current map. You can likely find it"
                f" either by visiting more exploration candidates, or perhaps by getting to a new"
                f" part of the current map via an intermediate map (e.g. through a building or"
                f" cave).",
            )

    return "\n".join(output)
