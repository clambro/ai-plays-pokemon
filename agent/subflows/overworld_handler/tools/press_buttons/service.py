"""Deterministic overworld button input."""

from typing import TYPE_CHECKING

from common.enums import Button, FacingDirection, MapId

if TYPE_CHECKING:
    from common.schemas import Coords
    from emulator.emulator import YellowLegacyEmulator
    from memory.rolling_memory import RollingMemory


async def press_buttons(
    *,
    rolling_memory: RollingMemory,
    emulator: YellowLegacyEmulator,
    buttons: list[Button],
) -> RollingMemory:
    """Execute a short overworld button sequence.

    Execution stops early after a collision, failed interaction, map transition, dialog, or battle.

    Args:
        rolling_memory: Recent memory to update with the decision and execution results.
        emulator: Running emulator used to inspect the state and press buttons.
        buttons: Buttons to press in order.

    Returns:
        The supplied rolling memory after recording the input and any early-stop feedback.
    """
    rolling_memory.add_memory(
        content=f"Selected the following buttons: {[str(button) for button in buttons]}.",
    )
    for button in buttons:
        game_state = await emulator.get_game_state()
        await emulator.press_button(button)
        passed_collision = await _check_for_collision(
            button=button,
            prev_map_id=game_state.map.id,
            prev_coords=game_state.player.coords,
            prev_direction=game_state.player.direction,
            rolling_memory=rolling_memory,
            emulator=emulator,
        )
        passed_action = await _check_for_action(
            button,
            rolling_memory=rolling_memory,
            emulator=emulator,
        )
        state_changed = await _check_for_state_change(emulator)
        if not passed_collision or not passed_action or state_changed:
            break
    return rolling_memory


async def _check_for_collision(  # noqa: PLR0913
    button: Button,
    prev_map_id: MapId,
    prev_coords: Coords,
    prev_direction: FacingDirection,
    *,
    rolling_memory: RollingMemory,
    emulator: YellowLegacyEmulator,
) -> bool:
    """Check whether a directional press collided or changed maps.

    Args:
        button: Button that was pressed.
        prev_map_id: Map ID before the button press.
        prev_coords: Player coordinates before the button press.
        prev_direction: Facing direction before the button press.
        rolling_memory: Recent memory to update after a collision or map transition.
        emulator: Running emulator used to inspect the resulting state.

    Returns:
        Whether execution may continue with the next planned button.
    """
    if button not in [Button.LEFT, Button.RIGHT, Button.UP, Button.DOWN]:
        return True

    game_state = await emulator.get_game_state()
    if prev_map_id != game_state.map.id:
        rolling_memory.add_memory(
            content=(
                f"I changed maps after pressing the '{button}' button. Cancelling further steps."
            ),
        )
        return False
    if prev_coords == game_state.player.coords and prev_direction == game_state.player.direction:
        rolling_memory.add_memory(
            content=(
                f"My position did not change after pressing the '{button}' button. Did I"
                f" bump into something?"
            ),
        )
        return False
    return True


async def _check_for_action(
    button: Button,
    *,
    rolling_memory: RollingMemory,
    emulator: YellowLegacyEmulator,
) -> bool:
    """Check whether an action-button press produced an interaction.

    Args:
        button: Button that was pressed.
        rolling_memory: Recent memory to update after the interaction.
        emulator: Running emulator used to inspect the resulting state.

    Returns:
        Whether execution may continue with the next planned button.
    """
    if button != Button.A:
        return True

    game_state = await emulator.get_game_state()
    if not game_state.is_text_on_screen():
        rolling_memory.add_memory(
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
        rolling_memory.add_memory(
            content=f'I pressed the action button and a dialog box opened, saying: "{text}"',
        )
        return False
    return True


async def _check_for_state_change(emulator: YellowLegacyEmulator) -> bool:
    """Check if the movement triggered a state change to dialog or a battle."""
    game_state = await emulator.get_game_state()
    return game_state.is_text_on_screen() or game_state.battle.is_in_battle
