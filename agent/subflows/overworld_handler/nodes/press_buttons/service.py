from loguru import logger

from agent.subflows.overworld_handler.nodes.press_buttons.prompts import PRESS_BUTTONS_PROMPT
from agent.subflows.overworld_handler.nodes.press_buttons.schemas import PressButtonsResponse
from common.enums import MapId
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button, FacingDirection
from memory.raw_memory import RawMemory, RawMemoryPiece


class PressButtonsService:
    """A service that presses buttons based on the current game state in the overworld."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH_LITE)

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def press_buttons(self) -> RawMemory:
        """Press buttons based on the current overworld game state."""
        game_state = self.emulator.get_game_state()
        img = self.emulator.get_screenshot()
        prompt = PRESS_BUTTONS_PROMPT.format(state=self.state_string_builder(game_state))
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=PressButtonsResponse,
                thinking_tokens=None,
                prompt_name="press_buttons",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error in the button pressing response. Skipping. {e}")
            return self.raw_memory

        if response.buttons:
            buttons = response.buttons if isinstance(response.buttons, list) else [response.buttons]
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"{response.thoughts} Selected the following buttons:"
                        f" {[str(b) for b in buttons]}."
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
                state_changed = await self._check_for_state_change()
                if not passed_collision or not passed_action or state_changed:
                    break

        return self.raw_memory

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

    async def _check_for_state_change(self) -> bool:
        """Check if the movement triggered a state change to dialog or a battle."""
        game_state = self.emulator.get_game_state()
        return game_state.is_text_on_screen() or game_state.battle.is_in_battle
