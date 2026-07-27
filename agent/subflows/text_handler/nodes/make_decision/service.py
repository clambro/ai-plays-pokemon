"""Business logic for make decision in the text subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.text_handler.nodes.make_decision.prompts import DECISION_MAKER_TEXT_PROMPT
from agent.subflows.text_handler.nodes.make_decision.schemas import DecisionMakerTextResponse
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService

if TYPE_CHECKING:
    from common.enums import Button
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from memory.raw_memory import RawMemory

llm_service = GeminiLLMService(GEMINI_FLASH_2_5)


async def make_decision(
    *,
    iteration: int,
    raw_memory: RawMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> RawMemory:
    """Make a decision based on the current text or menu state.

    Args:
        iteration: Current agent iteration used to timestamp the decision.
        raw_memory: Recent memory to update with the model response.
        state_string_builder: Formatter for the current game state.
        emulator: Running emulator used to inspect the screen and press buttons.

    Returns:
        The updated raw memory. Model failures are logged and leave the memory unchanged.
    """
    img = emulator.get_screenshot()
    game_state = emulator.get_game_state()
    state_string = state_string_builder(game_state)
    prompt = DECISION_MAKER_TEXT_PROMPT.format(
        state=state_string,
        text=game_state.screen.text,
    )
    try:
        response = await llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=DecisionMakerTextResponse,
            prompt_name="make_text_decision",
        )
        buttons = response.buttons if isinstance(response.buttons, list) else [response.buttons]
        raw_memory.add_memory(
            iteration=iteration,
            content=(
                f"{response.thoughts} Selected the following buttons: {[str(b) for b in buttons]}"
            ),
        )
        for b in buttons:
            game_state = emulator.get_game_state()
            await emulator.press_button(b)
            if _check_for_state_change(emulator) or _check_for_failed_action(
                b,
                game_state,
                iteration=iteration,
                raw_memory=raw_memory,
                emulator=emulator,
            ):
                break
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error making decision. Skipping. {e}")

    return raw_memory


def _check_for_state_change(emulator: YellowLegacyEmulator) -> bool:
    """Check if the button press triggered a state change to dialog or a battle."""
    game_state = emulator.get_game_state()
    return not game_state.is_text_on_screen() or game_state.battle.is_in_battle


def _check_for_failed_action(
    button: Button,
    game_state: YellowLegacyGameState,
    *,
    iteration: int,
    raw_memory: RawMemory,
    emulator: YellowLegacyEmulator,
) -> bool:
    """Check if the screen is unchanged following an action."""
    new_state = emulator.get_game_state()
    state_changed = new_state.screen.tiles == game_state.screen.tiles
    if state_changed:
        raw_memory.add_memory(
            iteration=iteration,
            content=f"I pressed the {button} button, but nothing happened. Have I made a mistake?",
        )
    return state_changed
