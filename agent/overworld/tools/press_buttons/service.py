"""Deterministic overworld button input."""

from typing import TYPE_CHECKING

from common.enums import Button, FacingDirection, MapId
from emulator.control_events import ControlBoundary

if TYPE_CHECKING:
    from common.schemas import Coords
    from emulator.emulator import Emulator
    from memory.rolling_memory.schemas import RollingMemory


async def press_buttons(
    *,
    rolling_memory: RollingMemory,
    emulator: Emulator,
    buttons: list[Button],
) -> str:
    """Execute a short overworld button sequence.

    Execution stops early after a collision, failed interaction, map transition, dialog, or battle.

    Args:
        rolling_memory: Recent memory to update with the decision and execution results.
        emulator: Running emulator used to inspect the state and press buttons.
        buttons: Buttons to press in order.

    Returns:
        The same action result recorded in rolling memory.
    """
    results = []
    for button in buttons:
        game_state = await emulator.get_game_state()
        control_result = await emulator.press_overworld_button(button)
        collision_result = await _check_for_collision(
            button=button,
            prev_map_id=game_state.map.id,
            prev_coords=game_state.player.coords,
            prev_direction=game_state.player.direction,
            emulator=emulator,
        )
        action_result = _check_for_action(button)
        if collision_result:
            results.append(collision_result)
        if action_result:
            results.append(action_result)
        control_left_overworld = control_result.boundary != ControlBoundary.OVERWORLD_READY
        if collision_result or action_result or control_left_overworld:
            break

    if not results:
        results.append("Button sequence completed.")
    result = "\n\n".join(results)
    rolling_memory.add_memory(result)
    return result


async def _check_for_collision(
    button: Button,
    prev_map_id: MapId,
    prev_coords: Coords,
    prev_direction: FacingDirection,
    *,
    emulator: Emulator,
) -> str | None:
    """Check whether a directional press collided or changed maps.

    Args:
        button: Button that was pressed.
        prev_map_id: Map ID before the button press.
        prev_coords: Player coordinates before the button press.
        prev_direction: Facing direction before the button press.
        emulator: Running emulator used to inspect the resulting state.

    Returns:
        Feedback when the sequence should stop, otherwise ``None``.
    """
    if button not in [Button.LEFT, Button.RIGHT, Button.UP, Button.DOWN]:
        return None

    game_state = await emulator.get_game_state()
    if prev_map_id != game_state.map.id:
        return f"Map changed from {prev_map_id.name} to {game_state.map.id.name}."
    if prev_coords == game_state.player.coords and prev_direction == game_state.player.direction:
        return (
            f"My position did not change after pressing the '{button}' button. Did I"
            " bump into something?"
        )
    return None


def _check_for_action(button: Button) -> str | None:
    """Check whether an action-button press produced an interaction.

    Args:
        button: Button that was pressed.

    Returns:
        Feedback when the sequence should stop, otherwise ``None``.
    """
    if button != Button.A:
        return None
    return "I pressed the action button."
