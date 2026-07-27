"""Business logic for press buttons in the overworld subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.overworld_handler.nodes.press_buttons.prompts import PRESS_BUTTONS_PROMPT
from agent.subflows.overworld_handler.nodes.press_buttons.schemas import PressButtonsResponse
from common.enums import Button, FacingDirection, MapId
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService

if TYPE_CHECKING:
    from common.schemas import Coords
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from memory.raw_memory import RawMemory

llm_service = GeminiLLMService(GEMINI_FLASH_2_5)


async def press_buttons(
    *,
    iteration: int,
    raw_memory: RawMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> RawMemory:
    """Ask the model for a short overworld button sequence and execute it.

    Execution stops early after a collision, failed interaction, map transition, dialog, or battle.

    Args:
        iteration: Current agent iteration used to timestamp the decision and feedback.
        raw_memory: Recent memory to update with the decision and execution results.
        state_string_builder: Formatter for the current overworld state and map context.
        emulator: Running emulator used to inspect the state and press buttons.

    Returns:
        The supplied raw memory after recording the decision and any early-stop feedback.
    """
    game_state = emulator.get_game_state()
    img = emulator.get_screenshot()
    last_memory = raw_memory.pieces.get(iteration) or ""
    prompt = PRESS_BUTTONS_PROMPT.format(
        state=state_string_builder(game_state),
        last_memory=last_memory,
    )
    try:
        response = await llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=PressButtonsResponse,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error in the button pressing response. Skipping. {e}")
        return raw_memory

    buttons = response.buttons if isinstance(response.buttons, list) else [response.buttons]
    raw_memory.add_memory(
        iteration=iteration,
        content=(
            f"{response.thoughts} Selected the following buttons: {[str(b) for b in buttons]}."
        ),
    )
    for b in buttons:
        game_state = emulator.get_game_state()
        await emulator.press_button(b)
        passed_collision = _check_for_collision(
            button=b,
            prev_map_id=game_state.map.id,
            prev_coords=game_state.player.coords,
            prev_direction=game_state.player.direction,
            iteration=iteration,
            raw_memory=raw_memory,
            emulator=emulator,
        )
        passed_action = _check_for_action(
            b,
            iteration=iteration,
            raw_memory=raw_memory,
            emulator=emulator,
        )
        state_changed = _check_for_state_change(emulator)
        if not passed_collision or not passed_action or state_changed:
            break
    return raw_memory


def _check_for_collision(  # noqa: PLR0913
    button: Button,
    prev_map_id: MapId,
    prev_coords: Coords,
    prev_direction: FacingDirection,
    *,
    iteration: int,
    raw_memory: RawMemory,
    emulator: YellowLegacyEmulator,
) -> bool:
    """Check whether a directional press collided or changed maps.

    Args:
        button: Button that was pressed.
        prev_map_id: Map ID before the button press.
        prev_coords: Player coordinates before the button press.
        prev_direction: Facing direction before the button press.
        iteration: Current agent iteration used to timestamp feedback.
        raw_memory: Recent memory to update after a collision or map transition.
        emulator: Running emulator used to inspect the resulting state.

    Returns:
        Whether execution may continue with the next planned button.
    """
    if button not in [Button.LEFT, Button.RIGHT, Button.UP, Button.DOWN]:
        return True

    game_state = emulator.get_game_state()
    if prev_map_id != game_state.map.id:
        raw_memory.add_memory(
            iteration=iteration,
            content=(
                f"I changed maps after pressing the '{button}' button. Cancelling further steps."
            ),
        )
        return False
    if prev_coords == game_state.player.coords and prev_direction == game_state.player.direction:
        raw_memory.add_memory(
            iteration=iteration,
            content=(
                f"My position did not change after pressing the '{button}' button. Did I"
                f" bump into something?"
            ),
        )
        return False
    return True


def _check_for_action(
    button: Button,
    *,
    iteration: int,
    raw_memory: RawMemory,
    emulator: YellowLegacyEmulator,
) -> bool:
    """Check whether an action-button press produced an interaction.

    Args:
        button: Button that was pressed.
        iteration: Current agent iteration used to timestamp feedback.
        raw_memory: Recent memory to update after the interaction.
        emulator: Running emulator used to inspect the resulting state.

    Returns:
        Whether execution may continue with the next planned button.
    """
    if button != Button.A:
        return True

    game_state = emulator.get_game_state()
    if not game_state.is_text_on_screen():
        raw_memory.add_memory(
            iteration=iteration,
            content=(
                "I pressed the action button but nothing happened. There must not be"
                " anything to interact with in the direction I am facing."
            ),
        )
        return False
    if dialog_box := game_state.get_dialog_box():
        # Some dialog boxes (e.g. if you pick up an item) disappear automatically before we can
        # start a new agent loop to parse them, so we have to capture them immediately.
        text = f"{dialog_box.top_line} {dialog_box.bottom_line}".strip()
        raw_memory.add_memory(
            iteration=iteration,
            content=f'I pressed the action button and a dialog box opened, saying: "{text}"',
        )
        return False
    return True


def _check_for_state_change(emulator: YellowLegacyEmulator) -> bool:
    """Check if the movement triggered a state change to dialog or a battle."""
    game_state = emulator.get_game_state()
    return game_state.is_text_on_screen() or game_state.battle.is_in_battle
