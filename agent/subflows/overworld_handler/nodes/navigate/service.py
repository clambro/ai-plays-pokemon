from loguru import logger

from agent.subflows.overworld_handler.nodes.navigate import formatting, utils
from agent.subflows.overworld_handler.nodes.navigate.prompts import DETERMINE_TARGET_COORDS_PROMPT
from agent.subflows.overworld_handler.nodes.navigate.schemas import NavigationResponse
from common.enums import Button, FacingDirection, MapId
from common.schemas import Coords
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService
from memory.raw_memory import RawMemory
from overworld_map.schemas import OverworldMap
from overworld_map.service import update_map_with_screen_info


class NavigationService:
    """
    The service for the navigation action.

    This handles all emulator interactions for navigation. The specific pathfinding algorithms are
    in the utils module, and the formatting of the data for the LLM is in the formatting module.
    """

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
        game_state = self.emulator.get_game_state()
        accessible_coords = await utils.get_accessible_coords(
            game_state.player.coords,
            self.current_map,
        )
        try:
            coords = await self._determine_target_coords(accessible_coords)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error determining target coordinates. Skipping. {e}")
            return self.current_map, self.raw_memory

        if coords not in accessible_coords:
            logger.warning("Cancelling navigation due to invalid target coordinates.")
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=(
                    f"Navigation failed. The target coordinates {coords} are not in the list of"
                    f" accessible coordinates that was provided to me."
                ),
            )
            return self.current_map, self.raw_memory

        path = await utils.calculate_path_to_target(
            game_state.player.coords,
            coords,
            self.current_map,
        )
        if not path:
            logger.warning("No path found to target coordinates.")
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=(
                    f"Navigation failed. No path found to target coordinates {coords}."
                    f" This either means that the location is inaccessible, or that I have not"
                    f" explored enough of the map to reveal the path."
                ),
            )
            return self.current_map, self.raw_memory

        starting_map_id = self.current_map.id
        await self._handle_pikachu(path[0])
        for button in path:
            await self.emulator.press_button(button)

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

    async def _determine_target_coords(self, accessible_coords: list[Coords]) -> Coords:
        """Determine the target coordinates to navigate to."""
        # Get algorithmic data.
        exploration_candidates = utils.get_exploration_candidates(
            accessible_coords,
            self.current_map,
        )
        boundary_tiles = utils.get_map_boundary_tiles(accessible_coords, self.current_map)

        # Format data for LLM.
        formatted_accessible_coords = formatting.format_coordinates_grid(accessible_coords)
        formatted_exploration_candidates = formatting.format_exploration_candidates(
            exploration_candidates
        )
        formatted_map_boundaries = formatting.format_map_boundary_tiles(
            boundary_tiles,
            formatting.get_map_connections(self.current_map),
        )

        # Get model response.
        img = self.emulator.get_screenshot()
        game_state = self.emulator.get_game_state()
        last_memory = self.raw_memory.pieces.get(self.iteration) or ""

        prompt = DETERMINE_TARGET_COORDS_PROMPT.format(
            state=self.state_string_builder(game_state),
            accessible_coords=formatted_accessible_coords,
            exploration_candidates=formatted_exploration_candidates,
            map_boundaries=formatted_map_boundaries,
            last_memory=last_memory,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=NavigationResponse,
            prompt_name="determine_target_coords",
        )
        self.raw_memory.add_memory(
            iteration=self.iteration,
            content=f"{response.thoughts} Navigating to {response.coords}.",
        )
        return response.coords

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
            await self.emulator.press_button(Button.UP)
        elif (
            button == Button.DOWN
            and player_pos.row == pikachu_pos.row - 1
            and facing != FacingDirection.DOWN
        ):
            await self.emulator.press_button(Button.DOWN)
        elif (
            button == Button.LEFT
            and player_pos.col == pikachu_pos.col + 1
            and facing != FacingDirection.LEFT
        ):
            await self.emulator.press_button(Button.LEFT)
        elif (
            button == Button.RIGHT
            and player_pos.col == pikachu_pos.col - 1
            and facing != FacingDirection.RIGHT
        ):
            await self.emulator.press_button(Button.RIGHT)

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
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=f"Navigation to {target_pos} interrupted at position {new_pos}.",
            )
            return True
        if game_state.map.id != starting_map_id:
            logger.warning("Map changed during navigation. Cancelling.")
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content="The map has changed during navigation. Cancelling further steps.",
            )
            return True
        return False
