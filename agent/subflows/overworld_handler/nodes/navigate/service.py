from loguru import logger

from agent.subflows.overworld_handler.nodes.navigate.prompts import DETERMINE_TARGET_COORDS_PROMPT
from agent.subflows.overworld_handler.nodes.navigate.schemas import NavigationResponse
from common.enums import AsciiTiles, MapId
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button, FacingDirection
from emulator.game_state import YellowLegacyGameState
from memory.raw_memory import RawMemory, RawMemoryPiece
from overworld_map.schemas import OverworldMap
from overworld_map.service import update_map_with_screen_info


class NavigationService:
    """The service for the navigation action."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

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
        try:
            coords = await self._determine_target_coords()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error determining target coordinates. Skipping. {e}")
            return self.current_map, self.raw_memory

        if not self._validate_target_coords(coords):
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

            prev_pos = (game_state.player.y, game_state.player.x)
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

    async def _determine_target_coords(self) -> tuple[int, int]:
        """Determine the target coordinates to navigate to."""
        img = self.emulator.get_screenshot()
        game_state = self.emulator.get_game_state()
        prompt = DETERMINE_TARGET_COORDS_PROMPT.format(
            state=self.state_string_builder(game_state),
            walkable_tiles=", ".join(f'"{t}"' for t in AsciiTiles.get_walkable_tiles()),
            exploration_candidates=self._get_exploration_candidates(),
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

    def _get_exploration_candidates(self) -> str:
        """Get all walkable tiles that are adjacent to an unseen tile."""
        tiles = self.current_map.ascii_tiles_ndarray
        walkable_tiles = AsciiTiles.get_walkable_tiles()

        candidates = []
        height, width = tiles.shape
        for y in range(height):
            for x in range(width):
                if tiles[y, x] not in walkable_tiles:
                    continue
                for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width and tiles[ny, nx] == AsciiTiles.UNSEEN:
                        candidates.append((y, x))
                        break

        if not candidates:
            return "No exploration candidates found."

        return ", ".join(f"({y}, {x})" for y, x in candidates)

    def _validate_target_coords(self, coords: tuple[int, int]) -> bool:
        """Validate the target coordinates."""
        row, col = coords
        if row < 0 or col < 0 or row >= self.current_map.height or col >= self.current_map.width:
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"Navigation failed. Target coordinates ({row}, {col}) are outside of the"
                        f" {self.current_map.id.name} map boundary."
                    ),
                ),
            )
            return False

        game_state = self.emulator.get_game_state()
        if row == game_state.player.y and col == game_state.player.x:
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"Navigation failed. Target coordinates ({row}, {col}) are the same as my"
                        f" current position. I am already there."
                    ),
                ),
            )
            return False

        target_tile = self.current_map.ascii_tiles_ndarray[row, col]
        if target_tile == AsciiTiles.UNSEEN:
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"Navigation failed. Target coordinates ({row}, {col}) are unexplored."
                        f" I must explore this area before I can navigate to it."
                    ),
                ),
            )
            return False
        if target_tile not in AsciiTiles.get_walkable_tiles():
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"Navigation failed. Target coordinates ({row}, {col}) are on a"
                        f' non-walkable tile of type "{target_tile}".'
                    ),
                ),
            )
            return False

        return True

    def _calculate_path_to_target(
        self,
        target_pos: tuple[int, int],
        game_state: YellowLegacyGameState,
    ) -> list[Button] | None:
        """
        Calculate the path to the target coordinates as a list of button presses using the A* search
        algorithm.
        """
        start_pos = (game_state.player.y, game_state.player.x)

        def _get_distance(a: tuple[int, int], b: tuple[int, int]) -> float:
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def _get_neighbors(pos: tuple[int, int]) -> list[tuple[int, int]]:
            y, x = pos
            neighbors = []
            for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_y, new_x = y + dy, x + dx
                if 0 <= new_y < self.current_map.height and 0 <= new_x < self.current_map.width:
                    target_tile = self.current_map.ascii_tiles_ndarray[new_y, new_x]
                    if target_tile in AsciiTiles.get_walkable_tiles():
                        neighbors.append((new_y, new_x))
                    elif target_tile == AsciiTiles.LEDGE and dy == 1:
                        # Account for the fact that we can jump down ledges, skipping a tile.
                        neighbors.append((new_y + 1, new_x))
            return neighbors

        open_set = {start_pos}
        came_from = {}
        g_score = {start_pos: 0}
        f_score = {start_pos: _get_distance(start_pos, target_pos)}

        while open_set:
            current = min(open_set, key=lambda pos: f_score.get(pos, float("inf")))

            if current == target_pos:
                # Reconstruct path and convert to button presses
                path = []
                while current in came_from:
                    prev = came_from[current]
                    # Calculate direction
                    dy = current[0] - prev[0]
                    dx = current[1] - prev[1]

                    # Convert direction to button
                    if dy > 0:
                        path.append(Button.DOWN)
                    elif dy < 0:
                        path.append(Button.UP)
                    elif dx > 0:
                        path.append(Button.RIGHT)
                    elif dx < 0:
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

        player_pos = (game_state.player.y, game_state.player.x)
        facing = game_state.player.direction
        pikachu_pos = (game_state.pikachu.y, game_state.pikachu.x)
        if (
            button == Button.UP
            and player_pos[0] == pikachu_pos[0] + 1
            and facing != FacingDirection.UP
        ):
            await self.emulator.press_buttons([Button.UP])
            await self.emulator.wait_for_animation_to_finish()
        elif (
            button == Button.DOWN
            and player_pos[0] == pikachu_pos[0] - 1
            and facing != FacingDirection.DOWN
        ):
            await self.emulator.press_buttons([Button.DOWN])
            await self.emulator.wait_for_animation_to_finish()
        elif (
            button == Button.LEFT
            and player_pos[1] == pikachu_pos[1] + 1
            and facing != FacingDirection.LEFT
        ):
            await self.emulator.press_buttons([Button.LEFT])
            await self.emulator.wait_for_animation_to_finish()
        elif (
            button == Button.RIGHT
            and player_pos[1] == pikachu_pos[1] - 1
            and facing != FacingDirection.RIGHT
        ):
            await self.emulator.press_buttons([Button.RIGHT])
            await self.emulator.wait_for_animation_to_finish()

    def _should_cancel_navigation(
        self,
        game_state: YellowLegacyGameState,
        prev_pos: tuple[int, int],
        starting_map_id: MapId,
        target_pos: tuple[int, int],
    ) -> bool:
        """Check if we should cancel navigation."""
        new_pos = (game_state.player.y, game_state.player.x)
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
