from itertools import groupby

from loguru import logger

from agent.subflows.overworld_handler.nodes.navigate.prompts import DETERMINE_TARGET_COORDS_PROMPT
from agent.subflows.overworld_handler.nodes.navigate.schemas import NavigationResponse
from common.enums import AsciiTiles, BlockedDirection, Button, FacingDirection, MapId
from common.schemas import Coords
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService
from memory.raw_memory import RawMemory, RawMemoryPiece
from overworld_map.schemas import OverworldMap
from overworld_map.service import update_map_with_screen_info


class NavigationService:
    """The service for the navigation action."""

    llm_service = GeminiLLMService(GEMINI_FLASH_2_5)

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        current_map: OverworldMap,
        raw_memory: RawMemory,
        state_string_builder: StateStringBuilderT,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.current_map = current_map
        self.raw_memory = raw_memory
        self.state_string_builder = state_string_builder

    async def navigate(self) -> tuple[OverworldMap, RawMemory]:
        """Determine the target coordinates and navigate to them."""
        accessible_coords = self._get_accessible_coords()
        try:
            coords = await self._determine_target_coords(accessible_coords)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error determining target coordinates. Skipping. {e}")
            return self.current_map, self.raw_memory

        if not self._validate_target_coords(coords, accessible_coords):
            logger.warning("Cancelling navigation due to invalid target coordinates.")
            return self.current_map, self.raw_memory

        game_state = self.emulator.get_game_state()
        path = self._calculate_path_to_target(coords, game_state)
        if not path:
            logger.warning("No path found to target coordinates.")
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"Navigation failed. No path found to target coordinates {coords}."
                        f" This either means that the location is inaccessible, or that I have not"
                        f" explored enough of the map to reveal the path."
                    ),
                ),
            )
            return self.current_map, self.raw_memory

        starting_map_id = self.current_map.id
        await self._handle_pikachu(path[0])
        for button in path:
            await self.emulator.press_buttons([button])
            await self.emulator.wait_for_animation_to_finish()

            prev_pos = game_state.player.coords
            game_state = self.emulator.get_game_state()
            if self._should_cancel_navigation(game_state, prev_pos, starting_map_id, coords):
                return self.current_map, self.raw_memory
            # Can't update the map until we validate above that we haven't switched maps.
            self.current_map = await update_map_with_screen_info(
                self.iteration,
                game_state,
                self.current_map,
            )
        return self.current_map, self.raw_memory

    def _get_accessible_coords(self) -> list[Coords]:
        """Recursively search outward from the player's position to find all accessible coords."""
        game_state = self.emulator.get_game_state()
        start_pos = game_state.player.coords
        walkable_tiles = AsciiTiles.get_walkable_tiles()
        visited = {start_pos}
        queue = [start_pos]
        accessible = []  # No need to return the starting position because we're already there.

        while queue:
            current = queue.pop(0)
            for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_pos = current + (dy, dx)  # noqa: RUF005
                if (
                    new_pos in visited
                    or new_pos.row < 0
                    or new_pos.row >= self.current_map.height
                    or new_pos.col < 0
                    or new_pos.col >= self.current_map.width
                ):
                    continue
                target_tile = self.current_map.ascii_tiles_ndarray[new_pos.row, new_pos.col]
                move_blocked = self._is_blocked(current, dy, dx, game_state)
                if target_tile in walkable_tiles and not move_blocked:
                    visited.add(new_pos)
                    queue.append(new_pos)
                    accessible.append(new_pos)
                # Jumping over a ledge skips a tile.
                elif target_tile == AsciiTiles.LEDGE_DOWN and dy == 1:
                    ledge_pos = new_pos + (1, 0)  # noqa: RUF005
                    if ledge_pos not in visited:
                        visited.add(ledge_pos)
                        queue.append(ledge_pos)
                        accessible.append(ledge_pos)
                elif target_tile == AsciiTiles.LEDGE_LEFT and dx == -1:
                    ledge_pos = new_pos + (0, -1)  # noqa: RUF005
                    if ledge_pos not in visited:
                        visited.add(ledge_pos)
                        queue.append(ledge_pos)
                        accessible.append(ledge_pos)
                elif target_tile == AsciiTiles.LEDGE_RIGHT and dx == 1:
                    ledge_pos = new_pos + (0, 1)  # noqa: RUF005
                    if ledge_pos not in visited:
                        visited.add(ledge_pos)
                        queue.append(ledge_pos)
                        accessible.append(ledge_pos)

        return accessible

    async def _determine_target_coords(self, accessible_coords: list[Coords]) -> Coords:
        """Determine the target coordinates to navigate to."""
        img = self.emulator.get_screenshot()
        game_state = self.emulator.get_game_state()
        last_memory = self.raw_memory.pieces.get(self.iteration) or ""
        prompt = DETERMINE_TARGET_COORDS_PROMPT.format(
            state=self.state_string_builder(game_state),
            accessible_coords=self._format_coordinates_grid(accessible_coords),
            exploration_candidates=self._get_exploration_candidates(accessible_coords),
            map_boundaries=self._get_map_boundary_tiles(accessible_coords),
            last_memory=last_memory,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=NavigationResponse,
            prompt_name="determine_target_coords",
        )
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=f"{response.thoughts} Navigating to {response.coords}.",
            ),
        )
        return response.coords

    def _format_coordinates_grid(self, coordinates: list[Coords]) -> str:
        """
        Format a list of coordinates as a grid string with rows separated by newlines.

        [(0,0), (0,1), (1,0), (1,1), (1,2)]
        ->
        (0,0) (0,1)
        (1,0) (1,1) (1,2)
        """
        if not coordinates:
            return ""

        coordinates = sorted(coordinates, key=lambda c: (c.row, c.col))
        rows = []
        for _, row_coords in groupby(coordinates, key=lambda c: c.row):
            row_str = ", ".join(str(coord) for coord in row_coords)
            rows.append(row_str)

        return "\n".join(rows)

    def _get_exploration_candidates(self, accessible_coords: list[Coords]) -> str:
        """Get all accessible coords that are adjacent to an unseen tile."""
        candidates = []
        tiles = self.current_map.ascii_tiles_ndarray
        height, width = tiles.shape
        for c in accessible_coords:
            for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                ny, nx = c.row + dy, c.col + dx
                if 0 <= ny < height and 0 <= nx < width and tiles[ny, nx] == AsciiTiles.UNSEEN:
                    candidates.append(c)
                    break

        if not candidates:
            return "No exploration candidates found."

        return self._format_coordinates_grid(candidates)

    def _get_map_boundary_tiles(self, accessible_coords: list[Coords]) -> str:
        """Get all accessible coords that are on the map boundary."""
        tiles = self.current_map.ascii_tiles_ndarray
        height, width = tiles.shape
        north, south, east, west = "NORTH", "SOUTH", "EAST", "WEST"
        boundary_tiles = {
            north: [],
            south: [],
            east: [],
            west: [],
        }
        for c in accessible_coords:
            if c.row == 0:
                boundary_tiles[north].append(c)
            elif c.row == height - 1:
                boundary_tiles[south].append(c)
            elif c.col == 0:
                boundary_tiles[west].append(c)
            elif c.col == width - 1:
                boundary_tiles[east].append(c)

        output = []
        game_map = self.emulator.get_game_state().map
        for connection, direction in (
            (game_map.north_connection, north),
            (game_map.south_connection, south),
            (game_map.west_connection, west),
            (game_map.east_connection, east),
        ):
            if connection is not None and boundary_tiles[direction]:
                coord_str = ", ".join(str(c) for c in boundary_tiles[direction])
                output.append(
                    f"The {connection.name} map boundary at the far {direction} of the current map"
                    f" is accessible from {coord_str}."
                )
            elif connection is not None:
                output.append(
                    f"You have not yet discovered a valid path to the {connection.name} map"
                    f" boundary at the far {direction} of the current map."
                )

        return "\n".join(output)

    def _validate_target_coords(self, coords: Coords, accessible_coords: list[Coords]) -> bool:
        """Validate the target coordinates."""
        if coords not in accessible_coords:
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"Navigation failed. The target coordinates {coords} are not in the list of"
                        f" accessible coordinates that was provided to me."
                    ),
                ),
            )
            return False
        return True

    def _is_blocked(
        self,
        current: Coords,
        dy: int,
        dx: int,
        game_state: YellowLegacyGameState,
    ) -> bool:
        """Check if the movement is blocked by a paired tile collision."""
        blockages = game_state.get_ascii_screen().blockages[current.row][current.col]
        if dy == 1:
            return bool(blockages & BlockedDirection.DOWN)
        if dy == -1:
            return bool(blockages & BlockedDirection.UP)
        if dx == 1:
            return bool(blockages & BlockedDirection.RIGHT)
        if dx == -1:
            return bool(blockages & BlockedDirection.LEFT)
        return False

    def _calculate_path_to_target(
        self,
        target_pos: Coords,
        game_state: YellowLegacyGameState,
    ) -> list[Button] | None:
        """
        Calculate the path to the target coordinates as a list of button presses using the A* search
        algorithm.
        """
        start_pos = game_state.player.coords

        def _get_distance(a: Coords, b: Coords) -> float:
            return (a - b).length

        def _get_neighbors(pos: Coords) -> list[Coords]:
            neighbors = []
            for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_pos = pos + (dy, dx)  # noqa: RUF005
                if (
                    0 <= new_pos.row < self.current_map.height
                    and 0 <= new_pos.col < self.current_map.width
                ):
                    target_tile = self.current_map.ascii_tiles_ndarray[new_pos.row, new_pos.col]
                    move_blocked = self._is_blocked(pos, dy, dx, game_state)
                    if target_tile in AsciiTiles.get_walkable_tiles() and not move_blocked:
                        neighbors.append(new_pos)
                    # Account for the fact that we can jump ledges, skipping a tile.
                    elif target_tile == AsciiTiles.LEDGE_DOWN and dy == 1:
                        neighbors.append(new_pos + (1, 0))  # noqa: RUF005
                    elif target_tile == AsciiTiles.LEDGE_LEFT and dx == -1:
                        neighbors.append(new_pos + (0, -1))  # noqa: RUF005
                    elif target_tile == AsciiTiles.LEDGE_RIGHT and dx == 1:
                        neighbors.append(new_pos + (0, 1))  # noqa: RUF005
            return neighbors

        open_set = {start_pos}
        came_from: dict[Coords, Coords] = {}
        g_score = {start_pos: 0}
        f_score = {start_pos: _get_distance(start_pos, target_pos)}

        while open_set:
            current = min(open_set, key=lambda pos: f_score.get(pos, float("inf")))

            if current == target_pos:
                # Reconstruct path and convert to button presses
                path = []
                while current in came_from:
                    prev = came_from[current]
                    delta = current - prev

                    if delta.row > 0:
                        path.append(Button.DOWN)
                    elif delta.row < 0:
                        path.append(Button.UP)
                    elif delta.col > 0:
                        path.append(Button.RIGHT)
                    elif delta.col < 0:
                        path.append(Button.LEFT)

                    current = prev

                return list(reversed(path))  # Reverse to get start->target order

            open_set.remove(current)

            for neighbor in _get_neighbors(current):
                tentative_g_score = g_score[current] + 1

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + _get_distance(neighbor, target_pos)
                    open_set.add(neighbor)

        # If we get here, no path was found
        return None

    async def _handle_pikachu(self, button: Button) -> None:
        """
        Check if Pikachu is in the way and face it if so.

        Pikachu can block your path on the very first step of navigation if you are not facing it
        when you try to move.
        """
        game_state = self.emulator.get_game_state()
        if not game_state.pikachu.is_rendered:
            return

        player_pos = game_state.player.coords
        facing = game_state.player.direction
        pikachu_pos = game_state.pikachu.coords
        if (
            button == Button.UP
            and player_pos.row == pikachu_pos.row + 1
            and facing != FacingDirection.UP
        ):
            await self.emulator.press_buttons([Button.UP])
            await self.emulator.wait_for_animation_to_finish()
        elif (
            button == Button.DOWN
            and player_pos.row == pikachu_pos.row - 1
            and facing != FacingDirection.DOWN
        ):
            await self.emulator.press_buttons([Button.DOWN])
            await self.emulator.wait_for_animation_to_finish()
        elif (
            button == Button.LEFT
            and player_pos.col == pikachu_pos.col + 1
            and facing != FacingDirection.LEFT
        ):
            await self.emulator.press_buttons([Button.LEFT])
            await self.emulator.wait_for_animation_to_finish()
        elif (
            button == Button.RIGHT
            and player_pos.col == pikachu_pos.col - 1
            and facing != FacingDirection.RIGHT
        ):
            await self.emulator.press_buttons([Button.RIGHT])
            await self.emulator.wait_for_animation_to_finish()

    def _should_cancel_navigation(
        self,
        game_state: YellowLegacyGameState,
        prev_pos: Coords,
        starting_map_id: MapId,
        target_pos: Coords,
    ) -> bool:
        """Check if we should cancel navigation."""
        new_pos = game_state.player.coords
        if new_pos == target_pos:
            logger.info("Navigation to target coordinates completed.")
            return True
        if prev_pos == new_pos:
            logger.warning("Navigation interrupted. Cancelling.")
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(f"Navigation to {target_pos} interrupted at position {new_pos}."),
                ),
            )
            return True
        if game_state.map.id != starting_map_id:
            logger.warning("Map changed during navigation. Cancelling.")
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content="The map has changed during navigation. Cancelling further steps.",
                ),
            )
            return True
        return False
