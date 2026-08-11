"""Prompts for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from agent.overworld.tools.navigate import formatting, utils

if TYPE_CHECKING:
    from agent.context import AgentContext
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
        accessible_coords = formatting.format_coordinates_grid(accessible, current_map)
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
