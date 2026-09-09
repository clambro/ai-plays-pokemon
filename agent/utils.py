"""Lightweight movement and state helpers for gameplay agents."""

from typing import TYPE_CHECKING

from common.enums import Button
from emulator.control_events import ControlBoundary

if TYPE_CHECKING:
    from emulator.emulator import Emulator
    from emulator.game_state import GameState


async def move_cursor(emulator: Emulator, current_index: int, target_index: int) -> None:
    """Move a vertical menu cursor to the target index."""
    idx_diff = current_index - target_index
    if idx_diff > 0:
        button = Button.UP
    elif idx_diff < 0:
        button = Button.DOWN
    else:
        return

    for _ in range(abs(idx_diff)):
        await emulator.press_button(button)


def is_battle_handler_state(game_state: GameState) -> bool:
    """Determine whether the game state belongs to the battle handler."""
    # The nickname screen after catching a Pokemon is considered a battle state by the game,
    # but we need to route it to the text handler instead.
    return game_state.battle.is_in_battle and not game_state.is_naming_screen()


def is_text_handler_state(
    game_state: GameState,
    control_boundary: ControlBoundary | None,
) -> bool:
    """Determine whether the current state belongs to the text handler."""
    if is_battle_handler_state(game_state):
        return False
    if control_boundary is not None:
        return control_boundary != ControlBoundary.OVERWORLD_READY
    return game_state.is_text_on_screen() or game_state.map.height == 0 or game_state.map.width == 0


def is_overworld_handler_state(
    game_state: GameState,
    control_boundary: ControlBoundary | None,
) -> bool:
    """Determine whether the current state belongs to the overworld handler."""
    return not is_battle_handler_state(game_state) and not is_text_handler_state(
        game_state,
        control_boundary,
    )
