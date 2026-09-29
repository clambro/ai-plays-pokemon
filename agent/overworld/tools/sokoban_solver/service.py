"""Business logic for the overworld Sokoban solver tool."""

import math
from collections import deque
from typing import TYPE_CHECKING

from agent.overworld.tools.sokoban_solver.schemas import SokobanMap, SokobanState
from common.constants import ACTION_RESULT_LABEL, GAME_DIALOG_LABEL
from common.enums import BUTTON_DIRECTIONS, BUTTON_OFFSETS, AsciiTile, Button, SpriteLabel
from common.schemas import Coords
from emulator.control_events import ControlBoundary
from overworld_map.service import update_overworld_map
from overworld_map.tiles import get_directional_warp_coords, get_navigation_tiles
from overworld_map.traversal import is_blocked

if TYPE_CHECKING:
    from emulator.emulator import Emulator
    from emulator.game_state import GameState
    from memory.rolling_memory.schemas import RollingMemory
    from overworld_map.schemas import OverworldMap

FREE_TILE = "F"
WALL_TILE = "W"
WARP_TILE = "P"


async def solve_sokoban(
    *,
    iteration: int,
    emulator: Emulator,
    current_map: OverworldMap,
    rolling_memory: RollingMemory,
) -> str:
    """Solve known goals one at a time, reporting progress if interrupted."""
    game_state = await emulator.get_game_state()
    sokoban_map = _get_simplified_map(current_map, game_state)

    if not sokoban_map.boulders or not sokoban_map.goals:
        result = (
            f"{ACTION_RESULT_LABEL} I couldn't run the Sokoban solver because there were no"
            " boulders or goals."
        )
        rolling_memory.add_memory(result)
        return result

    completed = 0
    dialogs: list[str] = []
    interruption = None
    while sokoban_map.boulders and sokoban_map.goals:
        solution = _solve_sokoban(current_map, sokoban_map, game_state)
        if solution is None:
            interruption = (
                "The Sokoban solver was unable to find a solution. This is likely because I"
                " haven't explored enough of the map yet, or I need to get boulders from"
                " other locations first."
            )
            break
        interruption = await _execute_solution(emulator, solution, sokoban_map, dialogs)
        if interruption is not None:
            break
        completed += 1
        game_state = await emulator.get_game_state()
        await update_overworld_map(iteration, game_state, current_map)
        sokoban_map = _get_simplified_map(current_map, game_state)

    remaining = len(sokoban_map.goals)
    result = _include_dialog(
        f"I solved {completed} boulder goal{'s' if completed != 1 else ''}. "
        f"{remaining} known {'goal remains' if remaining == 1 else 'goals remain'}."
        + (f" {interruption}" if interruption else ""),
        "\n\n".join(dialogs),
    )
    rolling_memory.add_memory(result)
    return result


def _get_simplified_map(
    current_map: OverworldMap,
    game_state: GameState,
) -> SokobanMap:
    """Get a simplified map of the Sokoban puzzle with the boulders and goals."""
    navigation_tiles = get_navigation_tiles(current_map, game_state)
    boulders = {
        sprite.coords
        for entity_id in current_map.known_sprite_ids
        if (sprite := game_state.sprites.get(entity_id)) is not None
        and sprite.label == SpriteLabel.BOULDER
    }
    simplified_tiles = []
    goals = set()
    for row_idx, row in enumerate(navigation_tiles):
        simplified_row = []
        for col_idx, t in enumerate(row):
            terrain = current_map.terrain[row_idx][col_idx]
            if terrain in (AsciiTile.BOULDER_HOLE, AsciiTile.PRESSURE_PLATE):
                goals.add(Coords(row=row_idx, col=col_idx))

            if t in (AsciiTile.WARP, AsciiTile.BOULDER_HOLE):
                simplified_row.append(WARP_TILE)
            elif t in AsciiTile.get_walkable_tiles():
                simplified_row.append(FREE_TILE)
            else:
                simplified_row.append(WALL_TILE)
        simplified_tiles.append(simplified_row)
    # Occupied goals are already solved; leave their boulders as obstacles.
    occupied_goals = boulders & goals
    goals -= occupied_goals
    boulders -= occupied_goals
    for b in boulders:
        simplified_tiles[b.row][b.col] = FREE_TILE

    return SokobanMap(
        tiles=simplified_tiles,
        boulders=boulders,
        goals=goals,
        collision_tiles=[[block[2] for block in row] for row in game_state.map.background_blocks],
        directional_warps=get_directional_warp_coords(current_map, game_state),
    )


def _solve_sokoban(
    current_map: OverworldMap,
    sokoban_map: SokobanMap,
    game_state: GameState,
) -> list[Button] | None:
    """Find any goal using A* over pushes, reconstructing buttons only for the solution."""
    initial_state = SokobanState(
        player_coords=game_state.player.coords,
        boulders=frozenset(sokoban_map.boulders),
    )
    goal_distances = _get_goal_distances(sokoban_map, game_state)
    predecessors: dict[SokobanState, tuple[SokobanState, Button]] = {}
    g_score = {initial_state: 0}
    f_score = {
        initial_state: min(
            (goal_distances.get(boulder, math.inf) for boulder in initial_state.boulders),
            default=math.inf,
        )
    }
    if f_score[initial_state] == math.inf:
        return None
    open_set = {initial_state}

    while open_set:
        # On equal estimates, prefer progress toward a goal over unrelated sideways pushes.
        current_state = min(open_set, key=lambda state: (f_score[state], -g_score[state]))
        if current_state.boulders & sokoban_map.goals:
            return _reconstruct_solution(
                current_state, predecessors, current_map, sokoban_map, game_state
            )
        open_set.remove(current_state)
        next_g_score = g_score[current_state] + 1
        paths = _get_walking_paths(current_state, current_map, sokoban_map, game_state)
        for boulder in current_state.boulders:
            for button in (Button.RIGHT, Button.DOWN, Button.LEFT, Button.UP):
                offset = BUTTON_OFFSETS[button]
                standing = boulder - offset
                destination = boulder + offset
                if (
                    standing not in paths
                    or destination in current_state.boulders
                    or not _is_movement_possible(
                        current_map, standing, boulder, sokoban_map, game_state, is_boulder=False
                    )
                    or not _is_movement_possible(
                        current_map, standing, destination, sokoban_map, game_state, is_boulder=True
                    )
                ):
                    continue
                # In-game, a push moves the boulder but leaves the player on the standing tile.
                next_state = SokobanState(
                    player_coords=standing,
                    boulders=(current_state.boulders - {boulder}) | {destination},
                )
                if next_g_score >= g_score.get(next_state, math.inf):
                    continue
                remaining_distance = min(
                    (goal_distances.get(boulder, math.inf) for boulder in next_state.boulders),
                    default=math.inf,
                )
                if remaining_distance == math.inf:
                    continue
                predecessors[next_state] = (current_state, button)
                g_score[next_state] = next_g_score
                f_score[next_state] = next_g_score + remaining_distance
                open_set.add(next_state)

    return None


def _get_goal_distances(sokoban_map: SokobanMap, game_state: GameState) -> dict[Coords, int]:
    """Work backward from known goals to estimate the fewest remaining pushes.

    Ignore other boulders and the player's access to standing tiles, making this a lower bound.
    """
    walkable = {
        Coords(row=row, col=col)
        for row, tiles in enumerate(sokoban_map.tiles)
        for col, tile in enumerate(tiles)
        if tile == FREE_TILE
    } | sokoban_map.directional_warps
    distances = dict.fromkeys(sokoban_map.goals, 0)
    queue = deque(sokoban_map.goals)
    while queue:
        destination = queue.popleft()
        for offset in BUTTON_OFFSETS.values():
            boulder = destination - offset
            standing = boulder - offset
            if boulder in distances or boulder not in walkable or standing not in walkable:
                continue
            if game_state.map.is_boulder_push_terrain_legal(
                sokoban_map.collision_tiles, standing, destination
            ):
                distances[boulder] = distances[destination] + 1
                queue.append(boulder)
    return distances


def _get_walking_paths(
    state: SokobanState,
    current_map: OverworldMap,
    sokoban_map: SokobanMap,
    game_state: GameState,
) -> dict[Coords, tuple[Coords, Button] | None]:
    """Find reachable standing positions and their walking predecessors."""
    paths: dict[Coords, tuple[Coords, Button] | None] = {state.player_coords: None}
    queue = deque([state.player_coords])
    while queue:
        source = queue.popleft()
        for button in (Button.RIGHT, Button.DOWN, Button.LEFT, Button.UP):
            destination = source + BUTTON_OFFSETS[button]
            if (
                destination not in state.boulders
                and destination not in paths
                and _is_movement_possible(
                    current_map, source, destination, sokoban_map, game_state, is_boulder=False
                )
            ):
                paths[destination] = (source, button)
                queue.append(destination)
    return paths


def _reconstruct_solution(
    state: SokobanState,
    predecessors: dict[SokobanState, tuple[SokobanState, Button]],
    current_map: OverworldMap,
    sokoban_map: SokobanMap,
    game_state: GameState,
) -> list[Button]:
    """Reconstruct walking and push buttons only for the successful predecessor chain."""
    solution = []
    while state in predecessors:
        previous_state, button = predecessors[state]
        solution.append(button)
        paths = _get_walking_paths(previous_state, current_map, sokoban_map, game_state)
        position = state.player_coords
        while (step := paths[position]) is not None:
            position, button = step
            solution.append(button)
        state = previous_state
    return list(reversed(solution))


# Player movement needs remembered blockages; boulder movement needs live collision rules.
def _is_movement_possible(  # noqa: PLR0913
    current_map: OverworldMap,
    source: Coords,
    destination: Coords,
    sokoban_map: SokobanMap,
    game_state: GameState,
    *,
    is_boulder: bool,
) -> bool:
    """Check if a destination is valid (within bounds, walkable, and not blocked)."""
    if (
        destination.row < 0
        or destination.row >= len(sokoban_map.tiles)
        or destination.col < 0
        or destination.col >= len(sokoban_map.tiles[0])
    ):
        return False

    if is_boulder:
        if not game_state.map.is_boulder_push_terrain_legal(
            sokoban_map.collision_tiles,
            source,
            destination,
        ):
            return False
    else:
        direction = destination - source
        if is_blocked(source, direction.row, direction.col, current_map.blockages):
            return False

    tile = sokoban_map.tiles[destination.row][destination.col]
    return tile == FREE_TILE or (
        tile == WARP_TILE and (is_boulder or destination in sokoban_map.directional_warps)
    )


async def _execute_solution(
    emulator: Emulator,
    solution: list[Button],
    sokoban_map: SokobanMap,
    dialogs: list[str],
) -> str | None:
    """Execute one solution, append field dialog, and return any interruption."""
    is_strength_active = False
    for button in solution:
        game_state = await emulator.get_game_state()
        next_pos = game_state.player.coords + BUTTON_OFFSETS[button]

        activating_strength = not is_strength_active and next_pos in sokoban_map.boulders
        yielding_to_pikachu = next_pos == game_state.pikachu.coords
        if (activating_strength or yielding_to_pikachu) and not await _face_next_pos(
            emulator,
            button,
            game_state,
        ):
            return (
                "I stopped the Sokoban solver because control left the overworld."
                " I should call it again when I return."
            )

        if activating_strength:
            await emulator.press_button(Button.A)
            strength_dialog = await emulator.advance_text_dialog_until_overworld_ready()
            if strength_dialog:
                dialogs.append(strength_dialog)
            is_strength_active = True

        pushing_boulder = next_pos in sokoban_map.boulders
        game_state = await emulator.get_game_state()
        if not await _execute_step(
            emulator,
            button,
            game_state,
            boulder_coords=next_pos if pushing_boulder else None,
        ):
            return (
                "The Sokoban solver was interrupted during movement. If a battle or another"
                " temporary event caused this, I should call it again afterward."
            )

        if pushing_boulder:
            sokoban_map.boulders.remove(next_pos)
            sokoban_map.boulders.add(next_pos + BUTTON_OFFSETS[button])

    return None


async def _execute_step(
    emulator: Emulator,
    button: Button,
    game_state: GameState,
    *,
    boulder_coords: Coords | None,
) -> bool:
    """Execute one planned movement, including turning or the two-stage boulder push."""
    starting_coords = game_state.player.coords
    desired_direction = BUTTON_DIRECTIONS[button]
    pikachu_ahead = (
        game_state.pikachu.is_rendered
        and starting_coords + BUTTON_OFFSETS[button] == game_state.pikachu.coords
    )
    max_attempts = 3 if boulder_coords is not None else 2

    for attempt in range(max_attempts):
        result = await emulator.press_overworld_button(button)
        if result.boundary != ControlBoundary.OVERWORLD_READY:
            return False

        observed_state = await emulator.get_game_state()
        if boulder_coords is not None:
            boulder_still_present = any(
                sprite.label == SpriteLabel.BOULDER and sprite.coords == boulder_coords
                for sprite in observed_state.sprites.values()
            )
            if not boulder_still_present:
                return True
        elif observed_state.player.coords != starting_coords:
            return True

        needs_retry = boulder_coords is not None or (
            attempt == 0 and (game_state.player.direction != desired_direction or pikachu_ahead)
        )
        if not needs_retry:
            return False
    return False


async def _face_next_pos(
    emulator: Emulator,
    button: Button,
    game_state: GameState,
) -> bool:
    """Face the next position and report whether control remains in the overworld."""
    if game_state.player.direction == BUTTON_DIRECTIONS[button]:
        return True
    result = await emulator.press_overworld_button(button)
    return result.boundary == ControlBoundary.OVERWORLD_READY


def _include_dialog(result: str, dialog: str) -> str:
    """Include captured field-move dialog in the first-person action result."""
    sections = [f'{GAME_DIALOG_LABEL} "{dialog}"'] if dialog else []
    return "\n\n".join([*sections, f"{ACTION_RESULT_LABEL} {result}"])
