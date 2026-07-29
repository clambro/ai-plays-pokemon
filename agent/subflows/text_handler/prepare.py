"""Prepare the initial context for a text-agent run."""

from typing import TYPE_CHECKING

from agent.subflows.text_handler.context import TextContext

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.emulator import YellowLegacyEmulator


async def prepare_text_context(
    *,
    state: AgentState,
    emulator: YellowLegacyEmulator,
) -> TextContext:
    """Capture the actionable text screen and required dependencies."""
    game_state, screenshot = await emulator.get_game_state_with_screenshot()
    return TextContext(
        state=state,
        game_state=game_state,
        screenshot=screenshot,
        emulator=emulator,
    )
