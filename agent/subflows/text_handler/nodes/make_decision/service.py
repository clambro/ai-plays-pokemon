"""Business logic for make decision in the text subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.text_handler.nodes.make_decision.prompts import DECISION_MAKER_TEXT_PROMPT
from agent.subflows.text_handler.nodes.make_decision.schemas import DecisionMakerTextResponse
from llm.service import OpenAILLMService

if TYPE_CHECKING:
    from common.enums import Button
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from memory.rolling_memory import RollingMemory

llm_service = OpenAILLMService()


async def make_decision(
    *,
    rolling_memory: RollingMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> RollingMemory:
    """Make a decision based on the current text or menu state.

    Args:
        rolling_memory: Recent memory to update with the model response.
        state_string_builder: Formatter for the current game state.
        emulator: Running emulator used to inspect the screen and press buttons.

    Returns:
        The updated rolling memory. Model failures are logged and leave the memory unchanged.
    """
    game_state, img = await emulator.get_game_state_with_screenshot()
    state_string = state_string_builder(game_state)
    prompt = DECISION_MAKER_TEXT_PROMPT.format(
        state=state_string,
        text=game_state.screen.text,
    )
    try:
        response = await llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=DecisionMakerTextResponse,
        )
        buttons = response.buttons if isinstance(response.buttons, list) else [response.buttons]
        rolling_memory.add_memory(
            content=(
                f"{response.thoughts} Selected the following buttons: {[str(b) for b in buttons]}"
            ),
        )
        for b in buttons:
            game_state = await emulator.get_game_state()
            await emulator.press_button(b)
            if await _check_for_state_change(emulator) or await _check_for_failed_action(
                b,
                game_state,
                rolling_memory=rolling_memory,
                emulator=emulator,
            ):
                break
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error making decision. Skipping. {e}")

    return rolling_memory


async def _check_for_state_change(emulator: YellowLegacyEmulator) -> bool:
    """Check if the button press triggered a state change to dialog or a battle."""
    game_state = await emulator.get_game_state()
    return not game_state.is_text_on_screen() or game_state.battle.is_in_battle


async def _check_for_failed_action(
    button: Button,
    game_state: YellowLegacyGameState,
    *,
    rolling_memory: RollingMemory,
    emulator: YellowLegacyEmulator,
) -> bool:
    """Check if the screen is unchanged following an action."""
    new_state = await emulator.get_game_state()
    state_changed = new_state.screen.tiles == game_state.screen.tiles
    if state_changed:
        rolling_memory.add_memory(
            content=f"I pressed the {button} button, but nothing happened. Have I made a mistake?",
        )
    return state_changed
