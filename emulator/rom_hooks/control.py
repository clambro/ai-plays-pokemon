"""Observe control boundaries in the required Yellow Legacy ROM."""

from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from common.enums import Button
from emulator.control_events import (
    ControlBoundary,
    ControlHandoff,
    ControlResult,
    ControlResultWaiter,
)
from emulator.rom_hooks.core import RomHook, install_hooks
from emulator.text_events import TextEventKind

if TYPE_CHECKING:
    from pyboy import PyBoy

    from emulator.game_state import GameState


class _HookName(StrEnum):
    """Executable boundaries used by control coordination."""

    OVERWORLD_INPUT = auto()
    QUANTITY_READY = auto()
    BESPOKE_INTERFACE_READY = auto()
    LOW_SENSITIVITY_INPUT_ACCEPTED = auto()
    MENU_INPUT_ACCEPTED = auto()
    MENU_READY = auto()
    NAMING_INPUT_ACCEPTED = auto()
    NAMING_READY = auto()
    POKEDEX_PAGE_READY = auto()
    POKEDEX_PAGE_INPUT_ACCEPTED = auto()
    SURF_GAME_OVER_READY = auto()
    PLAYER_STEP_COMPLETED = auto()


class _ControlDomain(StrEnum):
    """The input engine currently waiting for an external decision."""

    IMMEDIATE = auto()
    MENU = auto()
    NAMING = auto()
    OVERWORLD = auto()


@dataclass(slots=True, kw_only=True)
class _PendingOperation:
    """One control operation waiting for a rendered decision boundary."""

    operation_id: int
    button: Button | None
    button_mask: int
    input_domain: _ControlDomain | None = None
    required_boundary: ControlBoundary | None = None
    observe_steps: bool = False
    accepted: bool = False
    handoff_requested: bool = False
    release_scheduled: bool = False
    render_ready_frame: int | None = None
    step_observations: list[GameState] = field(default_factory=list)


# Addresses and signatures from the required Yellow Legacy ROM build.
_HOOKS = (
    RomHook(
        name=_HookName.OVERWORLD_INPUT,
        bank=0x00,
        address=0x0286,  # OverworldLoopLessDelay.notSimulating
        signature=bytes.fromhex("f0 b3 cb 5f 28 06"),
    ),
    RomHook(
        name=_HookName.QUANTITY_READY,
        bank=0x00,
        address=0x2C35,  # DisplayChooseQuantityMenu.waitForKeyPressLoop
        signature=bytes.fromhex("cd 2b 38 f0 b3 cb"),
    ),
    RomHook(
        name=_HookName.BESPOKE_INTERFACE_READY,
        bank=0x01,
        address=0x429C,  # DisplayTitleScreen.titleScreenLoop
        signature=bytes.fromhex("cd f7 43 da 0f 43"),
    ),
    RomHook(
        name=_HookName.BESPOKE_INTERFACE_READY,
        bank=0x0D,
        address=0x7B62,  # SlotMachine_HandleInputWhileWheelsSpin
        signature=bytes.fromhex("cd 05 1e cd 2b 38"),
    ),
    RomHook(
        name=_HookName.BESPOKE_INTERFACE_READY,
        bank=0x10,
        address=0x5BD4,  # DisplayOptionMenu_.optionMenuLoop
        signature=bytes.fromhex("cd 2b 38 f0 b5 e6"),
    ),
    RomHook(
        name=_HookName.BESPOKE_INTERFACE_READY,
        bank=0x1C,
        address=0x4FE0,  # DisplayTownMap.inputLoop
        signature=bytes.fromhex("cd f1 57 cd 2b 38"),
    ),
    RomHook(
        name=_HookName.BESPOKE_INTERFACE_READY,
        bank=0x1C,
        address=0x512D,  # LoadTownMap_Fly.inputLoop
        signature=bytes.fromhex("e5 cd 05 1e cd 2b"),
    ),
    RomHook(
        name=_HookName.BESPOKE_INTERFACE_READY,
        bank=0x3A,
        address=0x4EC2,  # Printer_CheckPressingB
        signature=bytes.fromhex("f0 b4 e6 02 20 02"),
    ),
    RomHook(
        name=_HookName.LOW_SENSITIVITY_INPUT_ACCEPTED,
        bank=0x00,
        address=0x383E,  # JoypadLowSensitivity.newlyPressedButtons
        signature=bytes.fromhex("3e 1e e0 d5 c9 f0"),
    ),
    RomHook(
        name=_HookName.MENU_INPUT_ACCEPTED,
        bank=0x00,
        address=0x3AFE,  # HandleMenuInput_.keyPressed
        signature=bytes.fromhex("af ea 4b cc f0 b5"),
    ),
    RomHook(
        name=_HookName.MENU_READY,
        bank=0x00,
        address=0x3ACD,  # HandleMenuInput_.loop2, after PlaceMenuCursor and Delay3
        signature=bytes.fromhex("e5 fa 9a d0 a7 28"),
    ),
    RomHook(
        name=_HookName.NAMING_INPUT_ACCEPTED,
        bank=0x01,
        address=0x647F,  # DisplayNamingScreen.checkForPressedButton
        signature=bytes.fromhex("cb 27 38 06 23 23"),
    ),
    RomHook(
        name=_HookName.NAMING_READY,
        bank=0x01,
        address=0x6466,  # DisplayNamingScreen.inputLoop
        signature=bytes.fromhex("fa 26 cc f5 06 1c"),
    ),
    RomHook(
        name=_HookName.POKEDEX_PAGE_READY,
        bank=0x10,
        address=0x464F,  # NewPageButtonPressCheck.waitForButtonPress
        signature=bytes.fromhex("cd b9 01 f0 b4 e6"),
    ),
    RomHook(
        name=_HookName.POKEDEX_PAGE_INPUT_ACCEPTED,
        bank=0x10,
        address=0x4658,  # NewPageButtonPressCheck accepted A or B
        signature=bytes.fromhex("c9 8b 84 95 84 8b"),
    ),
    RomHook(
        name=_HookName.SURF_GAME_OVER_READY,
        bank=0x3E,
        address=0x4435,  # SurfingMinigame_GameOver.wait_press_a
        signature=bytes.fromhex("f0 b3 e6 01 c8 21"),
    ),
    RomHook(
        name=_HookName.PLAYER_STEP_COMPLETED,
        bank=0x3C,
        address=0x412D,  # _AdvancePlayerSprite.afterUpdateMapCoords
        signature=bytes.fromhex("fa c4 cf fe 07 c2"),
    ),
)

_BUTTON_MASKS = {
    Button.A: 1 << 0,
    Button.B: 1 << 1,
    Button.SELECT: 1 << 2,
    Button.START: 1 << 3,
    Button.RIGHT: 1 << 4,
    Button.LEFT: 1 << 5,
    Button.UP: 1 << 6,
    Button.DOWN: 1 << 7,
}

_NPC_MOVEMENT_SCRIPT_ADDRESS = 0xCC57
_JOYPAD_STATE_ADDRESS = 0xD730
_MOVEMENT_STATE_ADDRESS = 0xD736
_JOY_IGNORE_ADDRESS = 0xCD6B
_WALK_COUNTER_ADDRESS = 0xCFC4
_BATTLE_STATE_ADDRESS = 0xD057
_CURRENT_OPPONENT_ADDRESS = 0xD059
_PLAYER_MOVING_DIRECTION_ADDRESS = 0xD575
_JOY_PRESSED_ADDRESS = 0xFFB3
_JOY_HELD_ADDRESS = 0xFFB4
_MENU_INPUT_ADDRESS = 0xFFB5
_OVERWORLD_FLAGS_ADDRESS = 0xCD60

_SUPPRESSED_OR_SIMULATED_INPUT = (1 << 0) | (1 << 5) | (1 << 7)
_DOOR_LEDGE_OR_SPINNER_MOVEMENT = (1 << 1) | (1 << 6) | (1 << 7)
_BOULDER_MOVING = 1 << 1
_RENDER_FENCE_FRAMES = 3

_ACCEPTED_INPUT_HOOKS = {
    _HookName.LOW_SENSITIVITY_INPUT_ACCEPTED: (
        _ControlDomain.IMMEDIATE,
        _JOY_PRESSED_ADDRESS,
    ),
    _HookName.MENU_INPUT_ACCEPTED: (_ControlDomain.MENU, _MENU_INPUT_ADDRESS),
    _HookName.NAMING_INPUT_ACCEPTED: (_ControlDomain.NAMING, _JOY_PRESSED_ADDRESS),
    _HookName.POKEDEX_PAGE_INPUT_ACCEPTED: (
        _ControlDomain.IMMEDIATE,
        _JOY_HELD_ADDRESS,
    ),
}
_READY_HOOKS = {
    _HookName.QUANTITY_READY: (
        _ControlDomain.IMMEDIATE,
        ControlBoundary.INTERACTIVE_READY,
    ),
    _HookName.BESPOKE_INTERFACE_READY: (
        _ControlDomain.IMMEDIATE,
        ControlBoundary.INTERACTIVE_READY,
    ),
    _HookName.MENU_READY: (_ControlDomain.MENU, ControlBoundary.MENU_READY),
    _HookName.NAMING_READY: (
        _ControlDomain.NAMING,
        ControlBoundary.INTERACTIVE_READY,
    ),
    _HookName.POKEDEX_PAGE_READY: (
        _ControlDomain.IMMEDIATE,
        ControlBoundary.INTERACTIVE_READY,
    ),
}


class RomControlHooks:
    """Correlate injected buttons with hooked ROM decision boundaries."""

    def __init__(self, pyboy: PyBoy, results: ControlResultWaiter) -> None:
        """Keep the owner-thread emulator and asynchronous result handoff."""
        self._pyboy = pyboy
        self._results = results
        self._next_operation_id = 1
        self._pending: _PendingOperation | None = None
        self._completed_boundary: ControlBoundary | None = None
        self._current_domain = _ControlDomain.IMMEDIATE
        self._current_boundary: ControlBoundary | None = None
        self._step_completed_this_tick = False

    def install(self) -> None:
        """Validate the required ROM layout and register the control hooks."""
        install_hooks(self._pyboy, _HOOKS, self._handle_hook)

    @property
    def current_boundary(self) -> ControlBoundary | None:
        """Return the latest rendered external decision boundary."""
        return self._current_boundary

    def arm_button(self, button: Button) -> int:
        """Arm input at the rendered boundary in the ROM's current control domain."""
        if self._current_boundary is None:
            raise ControlHandoff
        return self._arm(button=button, input_domain=self._current_domain)

    def arm_overworld_button(
        self,
        button: Button,
        *,
        observe_steps: bool = False,
    ) -> int:
        """Arm overworld input only while the ROM still accepts external movement."""
        if self._current_domain != _ControlDomain.OVERWORLD or not self._is_overworld_ready():
            raise ControlHandoff
        return self._arm(
            button=button,
            input_domain=_ControlDomain.OVERWORLD,
            observe_steps=observe_steps,
        )

    def begin_raw_input(self) -> None:
        """Invalidate readiness before a dialog driver schedules its own input."""
        if self._pending is not None:
            raise RuntimeError("A control operation is already pending.")
        self._current_boundary = None

    def _arm(
        self,
        *,
        button: Button,
        input_domain: _ControlDomain,
        observe_steps: bool = False,
    ) -> int:
        """Create one correlated input operation before scheduling its pulse."""
        if self._pending is not None:
            raise RuntimeError("A control operation is already pending.")
        operation_id = self._next_operation_id
        self._next_operation_id += 1
        self._pending = _PendingOperation(
            operation_id=operation_id,
            button=button,
            button_mask=_BUTTON_MASKS[button],
            input_domain=input_domain,
            observe_steps=observe_steps,
        )
        self._current_boundary = None
        return operation_id

    def arm_boundary_wait(self, boundary: ControlBoundary | None = None) -> int:
        """Wait for a requested or arbitrary ready boundary after active ROM work."""
        if self._pending is not None:
            raise RuntimeError("A control operation is already pending.")
        operation_id = self._next_operation_id
        self._next_operation_id += 1
        self._pending = _PendingOperation(
            operation_id=operation_id,
            button=None,
            button_mask=0,
            required_boundary=boundary,
            accepted=True,
        )
        if self._current_boundary is not None and (
            boundary is None or boundary == self._current_boundary
        ):
            self._complete(self._current_boundary)
        return operation_id

    @property
    def needs_step_observation(self) -> bool:
        """Return whether this tick completed a requested player step."""
        return self._step_completed_this_tick

    def publish_tick(self, step_observation: GameState | None = None) -> None:
        """Capture step progress and publish completion after the tick rendered."""
        pending = self._pending
        if self._step_completed_this_tick:
            if pending is not None and pending.observe_steps and step_observation is not None:
                pending.step_observations.append(step_observation)
            self._step_completed_this_tick = False

        self._request_handoff_if_overworld_control_lost()
        self._observe_immediate_input()

        pending = self._pending
        if (
            pending is not None
            and pending.button is not None
            and (pending.accepted or pending.handoff_requested)
            and not pending.release_scheduled
        ):
            # Hook callbacks run inside tick(), where an immediate PyBoy release would be discarded
            # by that tick's event cleanup. Queue it here, between ticks, for the next frame.
            self._pyboy.button_release(pending.button)
            pending.release_scheduled = True

        if pending is not None and pending.handoff_requested:
            if (
                pending.button is not None
                and self._pyboy.memory[_JOY_HELD_ADDRESS] & pending.button_mask
            ):
                return
            self._results.publish_handoff(pending.operation_id)
            self._completed_boundary = None
            self._pending = None
            return

        if self._completed_boundary is None:
            return
        if pending is None or not pending.accepted:
            raise RuntimeError("Completed control operation was not armed.")
        if (pending.button is None and self._pyboy.memory[_JOY_HELD_ADDRESS] != 0) or (
            pending.button is not None
            and self._pyboy.memory[_JOY_HELD_ADDRESS] & pending.button_mask
        ):
            return
        self._results.publish(
            pending.operation_id,
            ControlResult(
                boundary=self._completed_boundary,
                step_observations=tuple(pending.step_observations),
            ),
        )
        self._completed_boundary = None
        self._pending = None

    def observe_text_event(self, kind: TextEventKind) -> None:
        """Track text-driven control domains without consuming their event journal."""
        if kind not in {
            TextEventKind.MAP_ENTITY_INTERACTION_STARTED,
            TextEventKind.MAP_ENTITY_INTERACTION_ENDED,
            TextEventKind.PAGE_COMPLETED,
            TextEventKind.AUTOMATIC_SCROLL,
        }:
            self._request_handoff_for_unaccepted_button()

        if kind == TextEventKind.INPUT_REQUIRED:
            self._current_domain = _ControlDomain.IMMEDIATE
            self._observe_ready_boundary(ControlBoundary.TEXT_INPUT_READY)
        elif kind == TextEventKind.SPECIAL_INTERFACE_OPENED:
            self._current_domain = _ControlDomain.IMMEDIATE
            self._observe_ready_boundary(ControlBoundary.INTERACTIVE_READY)
        elif kind == TextEventKind.MENU_CLOSED:
            pending = self._pending
            if (
                pending is not None
                and pending.input_domain == _ControlDomain.MENU
                and pending.accepted
            ):
                pending.input_domain = _ControlDomain.IMMEDIATE
            self._current_domain = _ControlDomain.IMMEDIATE
            self._current_boundary = None
        elif kind in {
            TextEventKind.INPUT_RESOLVED,
            TextEventKind.MENU_OPENED,
            TextEventKind.SPECIAL_INTERFACE_CLOSED,
            TextEventKind.INTERACTION_CLOSED,
            TextEventKind.OVERWORLD_ENTERED,
            TextEventKind.BATTLE_ENDED,
        }:
            self._current_domain = _ControlDomain.IMMEDIATE
            self._current_boundary = None

    def _handle_hook(self, name: _HookName) -> None:
        if accepted_input := _ACCEPTED_INPUT_HOOKS.get(name):
            self._observe_accepted_input(*accepted_input)
        elif ready := _READY_HOOKS.get(name):
            self._observe_ready(*ready)
        elif name == _HookName.SURF_GAME_OVER_READY:
            self._observe_ready(
                _ControlDomain.IMMEDIATE,
                ControlBoundary.INTERACTIVE_READY,
            )
        elif name == _HookName.OVERWORLD_INPUT:
            self._observe_overworld_input()
        elif name == _HookName.PLAYER_STEP_COMPLETED:
            self._observe_player_step_completed()

    def _observe_overworld_input(self) -> None:
        overworld_ready = self._is_overworld_ready()
        if overworld_ready:
            self._current_domain = _ControlDomain.OVERWORLD

        pending = self._pending
        held = self._pyboy.memory[_JOY_HELD_ADDRESS]
        pressed = self._pyboy.memory[_JOY_PRESSED_ADDRESS]
        if pending is None:
            if overworld_ready and held == 0:
                self._current_boundary = ControlBoundary.OVERWORLD_READY
            elif pressed or held:
                self._current_boundary = None
            return

        if pending.button is None:
            if overworld_ready and held == 0:
                self._observe_ready_boundary(ControlBoundary.OVERWORLD_READY)
            return

        if not pending.accepted:
            self._observe_unaccepted_overworld_button(pending, pressed)
            return

        if overworld_ready and not held & pending.button_mask:
            self._observe_ready_boundary(ControlBoundary.OVERWORLD_READY)

    def _observe_accepted_input(self, domain: _ControlDomain, input_address: int) -> None:
        """Record that the active input engine processed the requested button."""
        input_state = self._pyboy.memory[input_address]
        if input_state:
            self._current_boundary = None
        pending = self._pending
        if pending is None or pending.input_domain != domain or pending.accepted:
            return
        if input_state & pending.button_mask:
            self._accept_button(pending)

    def _observe_ready(self, domain: _ControlDomain, boundary: ControlBoundary) -> None:
        """Track and, when applicable, complete a prepared input boundary."""
        self._current_domain = domain
        held = self._pyboy.memory[_JOY_HELD_ADDRESS]
        if held == 0:
            self._current_boundary = boundary
        else:
            self._current_boundary = None
        pending = self._pending
        if pending is None:
            return
        if not pending.accepted and pending.button is not None and pending.input_domain != domain:
            self._request_handoff_for_unaccepted_button()
            return
        if pending.button is None:
            if held == 0:
                self._complete(boundary)
            return
        if not pending.accepted:
            return
        if held & pending.button_mask:
            return
        self._complete(boundary)

    def _observe_immediate_input(self) -> None:
        """Fence bespoke screens after their next accepted and released input poll."""
        pending = self._pending
        if (
            pending is None
            or pending.handoff_requested
            or pending.required_boundary is not None
            or pending.input_domain != _ControlDomain.IMMEDIATE
            or self._completed_boundary is not None
        ):
            return

        frame = self._pyboy.frame_count
        if not pending.accepted:
            input_state = (
                self._pyboy.memory[_JOY_PRESSED_ADDRESS] | self._pyboy.memory[_MENU_INPUT_ADDRESS]
            )
            if input_state & pending.button_mask:
                self._accept_button(pending)
            return

        input_released = not self._pyboy.memory[_JOY_HELD_ADDRESS] & pending.button_mask
        input_poll_cleared = not self._pyboy.memory[_MENU_INPUT_ADDRESS] & pending.button_mask
        if pending.render_ready_frame is None:
            if input_released and input_poll_cleared:
                pending.render_ready_frame = frame + _RENDER_FENCE_FRAMES
            return
        if frame >= pending.render_ready_frame:
            self._observe_ready_boundary(ControlBoundary.INTERACTIVE_READY)

    def _observe_player_step_completed(self) -> None:
        pending = self._pending
        if (
            pending is not None
            and pending.observe_steps
            and pending.accepted
            and self._pyboy.memory[_WALK_COUNTER_ADDRESS] == 0
        ):
            self._step_completed_this_tick = True

    def _accept_button(self, pending: _PendingOperation) -> None:
        """Record that the ROM consumed an injected button press."""
        pending.accepted = True
        self._current_boundary = None

    def _observe_unaccepted_overworld_button(
        self,
        pending: _PendingOperation,
        pressed: int,
    ) -> None:
        """Accept overworld input or hand it off after another domain takes control."""
        if pending.input_domain != _ControlDomain.OVERWORLD:
            self._request_handoff_for_unaccepted_button()
        elif pressed & pending.button_mask:
            self._accept_button(pending)

    def _request_handoff_for_unaccepted_button(self) -> None:
        """Cancel a held button when the ROM changes domains before consuming it."""
        pending = self._pending
        if pending is not None and pending.button is not None and not pending.accepted:
            pending.handoff_requested = True

    def _request_handoff_if_overworld_control_lost(self) -> None:
        """Cancel unaccepted overworld input as soon as scripted control takes over."""
        pending = self._pending
        if (
            pending is not None
            and pending.input_domain == _ControlDomain.OVERWORLD
            and not pending.accepted
            and not self._is_overworld_ready()
        ):
            pending.handoff_requested = True

    def _is_overworld_ready(self) -> bool:
        mem = self._pyboy.memory
        return (
            mem[_WALK_COUNTER_ADDRESS] == 0
            and mem[_JOY_IGNORE_ADDRESS] == 0
            and not mem[_JOYPAD_STATE_ADDRESS] & _SUPPRESSED_OR_SIMULATED_INPUT
            and not mem[_MOVEMENT_STATE_ADDRESS] & _DOOR_LEDGE_OR_SPINNER_MOVEMENT
            and not mem[_OVERWORLD_FLAGS_ADDRESS] & _BOULDER_MOVING
            and mem[_PLAYER_MOVING_DIRECTION_ADDRESS] == 0
            and mem[_NPC_MOVEMENT_SCRIPT_ADDRESS] == 0
            and mem[_BATTLE_STATE_ADDRESS] == 0
            and mem[_CURRENT_OPPONENT_ADDRESS] == 0
        )

    def _complete(self, boundary: ControlBoundary) -> None:
        pending = self._pending
        if pending is None or not pending.accepted or self._completed_boundary is not None:
            return
        if pending.required_boundary is not None and pending.required_boundary != boundary:
            return
        self._completed_boundary = boundary

    def _observe_ready_boundary(self, boundary: ControlBoundary) -> None:
        """Retain the latest live boundary and complete a compatible pending wait."""
        self._current_boundary = boundary
        self._complete(boundary)
