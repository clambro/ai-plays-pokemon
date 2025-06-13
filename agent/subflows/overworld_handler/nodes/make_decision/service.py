from loguru import logger

from agent.subflows.overworld_handler.enums import OverworldTool
from agent.subflows.overworld_handler.nodes.make_decision.prompts import MAKE_DECISION_PROMPT
from agent.subflows.overworld_handler.nodes.make_decision.schemas import (
    Decision,
    MakeDecisionResponse,
)
from common.enums import AsciiTiles, MapId
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button, FacingDirection
from memory.raw_memory import RawMemory, RawMemoryPiece
from overworld_map.schemas import OverworldMap


class MakeDecisionService:
    """A service that makes decisions based on the current game state in the overworld."""

    llm_service = GeminiLLMService(GeminiLLMEnum.PRO)

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        current_map: OverworldMap,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.current_map = current_map
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def make_decision(self) -> Decision:
        """Make a decision based on the current overworld game state."""
        game_state = self.emulator.get_game_state()
        img = self.emulator.get_screenshot()
        prompt = MAKE_DECISION_PROMPT.format(
            state=self.state_string_builder(game_state),
            walkable_tiles=", ".join(f'"{t}"' for t in AsciiTiles.get_walkable_tiles()),
            exploration_candidates=self._get_exploration_candidates(),
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=MakeDecisionResponse,
                prompt_name="make_overworld_decision",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")
            return Decision(
                raw_memory=self.raw_memory,
                tool=None,
                navigation_args=None,
            )

        position = (game_state.player.y, game_state.player.x)
        thought = (
            f"Current map: {game_state.map.id.name} at coordinates {position}, facing"
            f" {game_state.player.direction.name}. {response.thoughts}"
        )

        if response.navigation_args:
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=f"{thought} Navigating to {response.navigation_args}.",
                ),
            )
            return Decision(
                raw_memory=self.raw_memory,
                tool=OverworldTool.NAVIGATION,
                navigation_args=response.navigation_args,
            )
        if response.buttons:
            buttons = response.buttons if isinstance(response.buttons, list) else [response.buttons]
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"{thought} Selected the following buttons: {[str(b) for b in buttons]}."
                    ),
                ),
            )
            for b in buttons:
                await self.emulator.press_buttons([b])
                passed_collision = await self._check_for_collision(
                    button=b,
                    prev_map_id=game_state.map.id,
                    prev_coords=(game_state.player.y, game_state.player.x),
                    prev_direction=game_state.player.direction,
                )
                passed_action = await self._check_for_action(b)
                if not passed_collision or not passed_action:
                    break

        return Decision(
            raw_memory=self.raw_memory,
            tool=None,
            navigation_args=None,
        )

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

    async def _check_for_collision(
        self,
        button: Button,
        prev_map_id: MapId,
        prev_coords: tuple[int, int],
        prev_direction: FacingDirection,
    ) -> bool:
        """
        Check if the player bumped into a wall and add a note to the raw memory if so.
        Returns True if the check passed, False otherwise.
        """
        if button not in [Button.LEFT, Button.RIGHT, Button.UP, Button.DOWN]:
            return True

        await self.emulator.wait_for_animation_to_finish()
        game_state = self.emulator.get_game_state()
        if (
            prev_map_id == game_state.map.id
            and prev_coords == (game_state.player.y, game_state.player.x)
            and prev_direction == game_state.player.direction
        ):
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"My position did not change after pressing the '{button}' button. Did I"
                        f" bump into something?"
                    ),
                ),
            )
            return False
        return True

    async def _check_for_action(self, button: Button) -> bool:
        """
        Check if the player hit the action button but nothing happened.
        Returns True if the check passed, False otherwise.
        """
        if button != Button.A:
            return True

        await self.emulator.wait_for_animation_to_finish()
        game_state = self.emulator.get_game_state()
        if not game_state.is_text_on_screen():
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        "I pressed the action button but nothing happened. There must not be"
                        " anything to interact with in the direction I am facing."
                    ),
                ),
            )
            return False
        return True
