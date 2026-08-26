"""Agent-level policy for settling routine game dialog."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agent.schemas import ScriptedDisplacementObservation
from agent.utils import is_battle_handler_state
from common.constants import GAME_DIALOG_LABEL, SCRIPTED_LOOP_LABEL
from common.enums import MapId
from emulator.control_events import ControlBoundary
from overworld_map.service import record_map_entity_interactions
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from PIL import Image

    from agent.context import AgentContext
    from agent.state import AgentState
    from common.schemas import Coords
    from emulator.game_state import GameState

_SCRIPTED_DISPLACEMENT_WINDOW_ITERATIONS = 20
_SCRIPTED_DISPLACEMENT_REPETITION_THRESHOLD = 3


@dataclass(frozen=True, slots=True, kw_only=True)
class DialogSettlement:
    """Transcript and terminal observation produced by routine settlement."""

    transcript: str
    game_state: GameState
    screenshot: Image.Image
    control_boundary: ControlBoundary | None
    scripted_displacement_warning: str = ""


def _is_plain_text_dialog(game_state: GameState) -> bool:
    """Check whether visible dialog can be advanced without a decision."""
    # Text outside the dialog box usually indicates a menu or yes/no question,
    # which must be left for the agent rather than advanced automatically.
    return game_state.screen.is_dialog_box_on_screen and not game_state.is_text_on_screen(
        ignore_dialog_box=True
    )


async def settle_dialog(
    context: AgentContext,
) -> DialogSettlement:
    """Settle dialog owned by the originating action and capture its terminal observation.

    Consecutive routine interactions remain owned by the action that caused
    them, including transitions between overworld and battle text.

    Args:
        context: Shared agent state and emulator access.

    Returns:
        The captured transcript and an atomic observation taken after settlement.
    """
    game_state, control_boundary = await context.emulator.get_game_state_with_control_boundary()
    initial_state = game_state
    started_in_plain_dialog = (
        control_boundary == ControlBoundary.TEXT_INPUT_READY
        and not is_battle_handler_state(game_state)
        and _is_plain_text_dialog(game_state)
    )

    chunks = []
    advanced = False
    while True:
        if is_battle_handler_state(game_state) and control_boundary in {
            None,
            ControlBoundary.TEXT_INPUT_READY,
        }:
            chunk = await context.emulator.advance_battle_dialog()
        elif control_boundary == ControlBoundary.TEXT_INPUT_READY and _is_plain_text_dialog(
            game_state
        ):
            chunk = await context.emulator.advance_text_dialog()
        else:
            break

        advanced = True
        if chunk:
            chunks.append(chunk)
        game_state, control_boundary = await context.emulator.get_game_state_with_control_boundary()

    if not advanced and (pending := context.emulator.consume_pending_dialog()):
        chunks.append(pending)
    transcript = " ".join(chunks)
    await record_map_entity_interactions(
        context.state.iteration,
        context.emulator.consume_completed_map_entity_interactions(),
    )

    (
        final_state,
        screenshot,
        final_boundary,
    ) = await context.emulator.get_game_state_with_screenshot_and_control_boundary()
    if transcript:
        context.state.rolling_memory.add_memory(
            content=f'{GAME_DIALOG_LABEL} "{transcript}"',
        )
    scripted_displacement_warning = ""
    if (
        advanced
        and started_in_plain_dialog
        and final_boundary == ControlBoundary.OVERWORLD_READY
        and initial_state.map.id == final_state.map.id
        and final_state.map.id not in {MapId.OUTSIDE, MapId.UNKNOWN}
        and initial_state.player.coords != final_state.player.coords
    ):
        scripted_displacement_warning = (
            _record_scripted_displacement(
                context.state,
                map_id=final_state.map.id,
                destination=final_state.player.coords,
            )
            or ""
        )
        if scripted_displacement_warning:
            context.state.rolling_memory.add_memory(scripted_displacement_warning)
            context.state.public_log.add(
                context.state.iteration,
                scripted_displacement_warning,
            )
    update_background_from_states(context.state, final_state)
    return DialogSettlement(
        transcript=transcript,
        game_state=final_state,
        screenshot=screenshot,
        control_boundary=final_boundary,
        scripted_displacement_warning=scripted_displacement_warning,
    )


def _record_scripted_displacement(
    state: AgentState,
    *,
    map_id: MapId,
    destination: Coords,
) -> str | None:
    """Record a dialog-owned displacement and flag a repeated destination.

    Args:
        state: Mutable gameplay state that owns the observation history.
        map_id: Map on which the displacement began and ended.
        destination: Player location after overworld control returned.

    Returns:
        A gameplay advisory once the destination has occurred at least three
        times in the rolling iteration window, otherwise ``None``.
    """
    earliest_iteration = state.iteration - _SCRIPTED_DISPLACEMENT_WINDOW_ITERATIONS + 1
    recent_observations = [
        observation
        for observation in state.scripted_displacements
        if earliest_iteration <= observation.iteration <= state.iteration
    ]
    observation = ScriptedDisplacementObservation(
        iteration=state.iteration,
        map_id=map_id,
        destination=destination,
    )
    state.scripted_displacements = [*recent_observations, observation]

    matching_observations = sum(
        previous.map_id == map_id and previous.destination == destination
        for previous in state.scripted_displacements
    )
    if matching_observations < _SCRIPTED_DISPLACEMENT_REPETITION_THRESHOLD:
        return None
    return (
        f"{SCRIPTED_LOOP_LABEL} I have been moved back to the same location by a scripted event"
        " repeatedly and in quick succession. This means I am likely pursuing the wrong path."
        " I should try something different. There is no way to sneak or force my way past a"
        " scripted event. It usually requires some other kind of in game progress."
    )
