"""Recall shortest known routes through observed map transitions."""

from collections import deque
from typing import TYPE_CHECKING

import numpy as np
from loguru import logger

from agent.overworld import navigation
from common.constants import ACTION_RESULT_LABEL
from common.enums import AsciiTile, Button, WarpActivation
from database.map_memory.repository import get_map_memory
from database.route_memory.repository import get_route_transitions

if TYPE_CHECKING:
    from collections.abc import Mapping

    from agent.overworld.tools.recall_route.schemas import RouteSearchState
    from common.enums import MapId
    from common.schemas import Coords
    from database.map_memory.schemas import MapMemoryRead
    from database.route_memory.schemas import RouteTransitionRead
    from memory.rolling_memory.schemas import RollingMemory


async def recall_route(
    *,
    destination: str,
    search: RouteSearchState,
    rolling_memory: RollingMemory,
) -> str:
    """Recall a shortest observed route to a visited map without moving the player."""
    destination_map_id = _resolve_destination(destination, search.visited_map_ids)
    if destination_map_id is None:
        result = f'I have not visited a map named "{destination}".'
    elif destination_map_id == search.map_id:
        result = f"I am already on {destination_map_id.name}."
    else:
        try:
            transitions = await get_route_transitions()
            map_ids = {transition.source_map_id for transition in transitions}
            map_memories = {
                map_id: memory
                for map_id in sorted(map_ids)
                if (memory := await get_map_memory(map_id)) is not None
            }
            route = find_route(
                search=search,
                destination_map_id=destination_map_id,
                transitions=transitions,
                map_memories=map_memories,
            )
        except Exception as error:  # noqa: BLE001
            logger.opt(exception=error).warning(
                "Route recall failed; continuing without remembered directions."
            )
            result = "I could not access my route memory right now."
        else:
            result = (
                _format_route(destination_map_id, route)
                if route is not None
                else f"I do not know a route from my current region to {destination_map_id.name}."
            )

    result = f"{ACTION_RESULT_LABEL} {result}"
    rolling_memory.add_memory(result)
    return result


def find_route(
    *,
    search: RouteSearchState,
    destination_map_id: MapId,
    transitions: list[RouteTransitionRead],
    map_memories: Mapping[MapId, MapMemoryRead],
) -> list[RouteTransitionRead] | None:
    """Find a shortest directed route through currently traversable explored terrain."""
    start = (search.map_id, search.coords)
    queue = deque([(start, [])])
    visited = {start}
    reachable_cache = {start: search.reachable_coords}

    while queue:
        location, route = queue.popleft()
        map_id, coords = location
        reachable = reachable_cache.get(location)
        if reachable is None:
            reachable = _get_reachable_coords(coords, map_memories.get(map_id), search.hm_tiles)
            reachable_cache[location] = reachable

        for transition in transitions:
            if transition.source_map_id != map_id or transition.source_coords not in reachable:
                continue
            next_route = [*route, transition]
            if transition.destination_map_id == destination_map_id:
                return next_route
            destination = (transition.destination_map_id, transition.destination_coords)
            if destination not in visited:
                visited.add(destination)
                queue.append((destination, next_route))

    return None


def _resolve_destination(destination: str, visited_map_ids: frozenset[MapId]) -> MapId | None:
    """Resolve a model-supplied name only against maps the player has visited."""
    normalized = destination.strip().upper().replace(" ", "_")
    return next((map_id for map_id in visited_map_ids if map_id.name == normalized), None)


def _get_reachable_coords(
    start: Coords,
    map_memory: MapMemoryRead | None,
    hm_tiles: list[AsciiTile],
) -> frozenset[Coords]:
    """Derive local reachability from one remembered arrival coordinate."""
    if map_memory is None:
        return frozenset()
    tiles = np.asarray([list(row) for row in map_memory.terrain.splitlines()])
    height, width = tiles.shape
    if not 0 <= start.row < height or not 0 <= start.col < width:
        return frozenset()
    tiles[start.row, start.col] = AsciiTile.PLAYER
    return frozenset(
        navigation.get_accessible_coords(
            start,
            tiles,
            map_memory.blockages,
            hm_tiles,
        )
    )


def _format_route(destination_map_id: MapId, route: list[RouteTransitionRead]) -> str:
    """Format an observed route as executable map-qualified directions."""
    steps = "\n".join(
        _format_transition(index, transition) for index, transition in enumerate(route, start=1)
    )
    return f"Known route to {destination_map_id.name}:\n{steps}"


def _format_transition(index: int, transition: RouteTransitionRead) -> str:
    """Describe how to execute one observed transition with the appropriate tool."""
    if transition.warp_activation == WarpActivation.STEP_ON:
        warp_coords = transition.source_coords + _BUTTON_OFFSETS[transition.button]
        action = f"navigate to the warp at {warp_coords}"
    elif transition.warp_activation is not None:
        action = (
            f"navigate to the warp at {transition.source_coords}, then press"
            f" {transition.warp_activation.value} twice"
        )
    else:
        action = (
            f"navigate to the map boundary at {transition.source_coords}, then press"
            f" {transition.button.value}"
        )
    return (
        f"{index}. On {transition.source_map_id.name}, {action} to reach"
        f" {transition.destination_map_id.name} at {transition.destination_coords}."
    )


_BUTTON_OFFSETS = {
    Button.UP: (-1, 0),
    Button.DOWN: (1, 0),
    Button.LEFT: (0, -1),
    Button.RIGHT: (0, 1),
}
