"""Agent-level policy for settling routine game dialog."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agent.utils import is_battle_handler_state
from emulator.control_events import ControlBoundary
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from PIL import Image

    from agent.context import AgentContext
    from emulator.game_state import GameState


@dataclass(frozen=True, slots=True, kw_only=True)
class DialogSettlement:
    """Transcript and terminal observation produced by routine settlement."""

    transcript: str
    game_state: GameState
    screenshot: Image.Image
    control_boundary: ControlBoundary | None


def _is_plain_text_dialog(game_state: GameState) -> bool:
    """Check whether visible dialog can be advanced without a decision."""
    # Text outside the dialog box usually indicates a menu or yes/no question,
    # which must be left for the agent rather than advanced automatically.
    return game_state.screen.is_dialog_box_on_screen and not game_state.is_text_on_screen(
        ignore_dialog_box=True
    )


async def settle_dialog(
    context: AgentContext,
    *,
    battle: bool = False,
) -> DialogSettlement:
    """Settle dialog owned by the originating action and capture its terminal observation.

    Ordinary actions advance consecutive plain-text interactions. Battle
    actions advance active resolution text and otherwise claim pending events
    without sending input.

    Args:
        context: Shared agent state and emulator access.
        battle: Whether battle resolution owns the pending dialog.

    Returns:
        The captured transcript and an atomic observation taken after settlement.
    """
    game_state, control_boundary = await context.emulator.get_game_state_with_control_boundary()
    in_battle = is_battle_handler_state(game_state)

    async def publish_before_input() -> None:
        current_state = await context.emulator.get_game_state()
        update_background_from_states(context.state, current_state)

    if battle:
        if in_battle and control_boundary in {
            None,
            ControlBoundary.TEXT_INPUT_READY,
        }:
            transcript = await context.emulator.advance_battle_dialog(
                before_input=publish_before_input,
            )
        else:
            transcript = context.emulator.consume_pending_dialog()
    elif in_battle:
        transcript = ""
    elif control_boundary == ControlBoundary.TEXT_INPUT_READY and _is_plain_text_dialog(game_state):
        chunks = []
        while (
            control_boundary == ControlBoundary.TEXT_INPUT_READY
            and not is_battle_handler_state(game_state)
            and _is_plain_text_dialog(game_state)
        ):
            chunk = await context.emulator.advance_text_dialog(
                before_input=publish_before_input,
            )
            if chunk:
                chunks.append(chunk)
            (
                game_state,
                control_boundary,
            ) = await context.emulator.get_game_state_with_control_boundary()
        transcript = " ".join(chunks)
    else:
        transcript = context.emulator.consume_pending_dialog()

    (
        final_state,
        screenshot,
        final_boundary,
    ) = await context.emulator.get_game_state_with_screenshot_and_control_boundary()
    if transcript:
        context.state.rolling_memory.add_memory(
            content=f'Onscreen text: "{transcript}"',
        )
    return DialogSettlement(
        transcript=transcript,
        game_state=final_state,
        screenshot=screenshot,
        control_boundary=final_boundary,
    )
