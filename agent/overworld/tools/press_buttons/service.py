"""Deterministic overworld button input."""

from typing import TYPE_CHECKING

from common.constants import ACTION_RESULT_LABEL
from common.enums import Button, FacingDirection, MapId
from emulator.control_events import ControlBoundary
from overworld_map.service import record_observed_route_transition

if TYPE_CHECKING:
    from common.schemas import Coords
    from emulator.emulator import Emulator
    from emulator.game_state import GameState
    from memory.rolling_memory.schemas import RollingMemory


async def press_buttons(
    *,
    iteration: int,
    rolling_memory: RollingMemory,
    emulator: Emulator,
    buttons: list[Button],
) -> str:
    """Execute a short overworld button sequence.

    Execution stops early after a collision, failed interaction, map transition, dialog, or battle.

    Args:
        iteration: Current agent iteration used to timestamp observed transitions.
        rolling_memory: Recent memory to update with the decision and execution results.
        emulator: Running emulator used to inspect the state and press buttons.
        buttons: Buttons to press in order.

    Returns:
        The same action result recorded in rolling memory.
    """
    results = []
    for button in buttons:
        previous = await emulator.get_game_state()
        control_result = await emulator.press_overworld_button(button)
        current = await emulator.get_game_state()
        await record_observed_route_transition(
            iteration=iteration,
            button=button,
            previous=previous,
            result=control_result,
            current=current,
        )
        collision_result = _check_for_collision(
            button=button,
            prev_map_id=previous.map.id,
            prev_coords=previous.player.coords,
            prev_direction=previous.player.direction,
            game_state=current,
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
    result = "\n\n".join(f"{ACTION_RESULT_LABEL} {entry}" for entry in results)
    rolling_memory.add_memory(result)
    return result


def _check_for_collision(
    button: Button,
    prev_map_id: MapId,
    prev_coords: Coords,
    prev_direction: FacingDirection,
    *,
    game_state: GameState,
) -> str | None:
    """Check whether a directional press collided or changed maps.

    Args:
        button: Button that was pressed.
        prev_map_id: Map ID before the button press.
        prev_coords: Player coordinates before the button press.
        prev_direction: Facing direction before the button press.
        game_state: State after the button press.

    Returns:
        Feedback when the sequence should stop, otherwise ``None``.
    """
    if button not in [Button.LEFT, Button.RIGHT, Button.UP, Button.DOWN]:
        return None

    if prev_map_id != game_state.map.id:
        return (
            f"Map changed from {prev_map_id.name} {prev_coords}"
            f" to {game_state.map.id.name} {game_state.player.coords}."
        )
    # Remaining stationary after changing direction is a successful turn, not a collision.
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
