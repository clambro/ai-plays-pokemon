"""Observe control boundaries in the required Yellow Legacy ROM."""

from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from common.enums import Button
from emulator.control_events import ControlBoundary, ControlResult, ControlResultWaiter
from emulator.text_events import TextEventKind

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyboy import PyBoy

    from emulator.game_state import GameState


class _HookName(StrEnum):
    """Executable boundaries used by control coordination."""

    OVERWORLD_INPUT = auto()
    MENU_INPUT_ACCEPTED = auto()
    MENU_READY = auto()
    NAMING_INPUT_ACCEPTED = auto()
    NAMING_READY = auto()
    PLAYER_STEP_COMPLETED = auto()


class _ControlDomain(StrEnum):
    """The input engine currently waiting for an external decision."""

    IMMEDIATE = auto()
    MENU = auto()
    NAMING = auto()
    OVERWORLD = auto()


@dataclass(frozen=True, slots=True, kw_only=True)
class _Hook:
    """One executable address and its required instruction signature."""

    name: _HookName
    bank: int
    address: int
    signature: bytes


@dataclass(slots=True, kw_only=True)
class _PendingOperation:
    """One requested input waiting for acceptance and a later decision boundary."""

    operation_id: int
    button: Button | None
    button_mask: int
    input_domain: _ControlDomain | None = None
    required_boundary: ControlBoundary | None = None
    observe_steps: bool = False
    accepted_frame: int | None = None
    render_ready_frame: int | None = None
    step_observations: list[GameState] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class _CompletedOperation:
    """Terminal boundary awaiting publication after the rendered tick."""

    boundary: ControlBoundary
    frame: int


# Addresses and signatures from the required Yellow Legacy ROM build.
_HOOKS = (
    _Hook(
        name=_HookName.OVERWORLD_INPUT,
        bank=0x00,
        address=0x0286,  # OverworldLoopLessDelay.notSimulating
        signature=bytes.fromhex("f0 b3 cb 5f 28 06"),
    ),
    _Hook(
        name=_HookName.MENU_INPUT_ACCEPTED,
        bank=0x00,
        address=0x3AFE,  # HandleMenuInput_.keyPressed
        signature=bytes.fromhex("af ea 4b cc f0 b5"),
    ),
    _Hook(
        name=_HookName.MENU_READY,
        bank=0x00,
        address=0x3ACD,  # HandleMenuInput_.loop2, after PlaceMenuCursor and Delay3
        signature=bytes.fromhex("e5 fa 9a d0 a7 28"),
    ),
    _Hook(
        name=_HookName.NAMING_INPUT_ACCEPTED,
        bank=0x01,
        address=0x647F,  # DisplayNamingScreen.checkForPressedButton
        signature=bytes.fromhex("cb 27 38 06 23 23"),
    ),
    _Hook(
        name=_HookName.NAMING_READY,
        bank=0x01,
        address=0x6466,  # DisplayNamingScreen.inputLoop
        signature=bytes.fromhex("fa 26 cc f5 06 1c"),
    ),
    _Hook(
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


class RomControlRecorder:
    """Correlate injected buttons with the ROM's next rendered decision boundary."""

    def __init__(self, pyboy: PyBoy, results: ControlResultWaiter) -> None:
        """Keep the owner-thread emulator and asynchronous result handoff."""
        self._pyboy = pyboy
        self._results = results
        self._next_operation_id = 1
        self._pending: _PendingOperation | None = None
        self._completed: _CompletedOperation | None = None
        self._current_domain = _ControlDomain.IMMEDIATE
        self._step_completed_this_tick = False

    def install(self) -> None:
        """Validate the required ROM layout and register the control hooks."""
        mismatch = next((hook for hook in _HOOKS if not self._signature_matches(hook)), None)
        if mismatch is not None:
            raise RuntimeError(
                f"Required ROM instruction signature does not match at {mismatch.name}."
            )

        for hook in _HOOKS:
            self._pyboy.hook_register(
                hook.bank,
                hook.address,
                self._build_callback(hook.name),
                None,
            )

    def arm_button(self, button: Button) -> int:
        """Arm input using the control domain most recently reached by the ROM."""
        return self._arm(button=button, input_domain=self._current_domain)

    def arm_overworld_button(self, button: Button, *, observe_steps: bool = False) -> int:
        """Arm an explicitly overworld-scoped button operation."""
        return self._arm(
            button=button,
            input_domain=_ControlDomain.OVERWORLD,
            observe_steps=observe_steps,
        )

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
        return operation_id

    def arm_boundary_wait(self, boundary: ControlBoundary) -> int:
        """Wait for a requested ready boundary after already-active ROM work."""
        if self._pending is not None:
            raise RuntimeError("A control operation is already pending.")
        operation_id = self._next_operation_id
        self._next_operation_id += 1
        self._pending = _PendingOperation(
            operation_id=operation_id,
            button=None,
            button_mask=0,
            required_boundary=boundary,
            accepted_frame=self._pyboy.frame_count,
        )
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

        self._observe_immediate_input()

        if self._completed is None:
            return
        if pending is None or pending.accepted_frame is None:
            raise RuntimeError("Completed control operation has no pending input.")
        if (
            pending.button is not None
            and self._pyboy.memory[_JOY_HELD_ADDRESS] & pending.button_mask
        ):
            return
        self._results.publish(
            ControlResult(
                operation_id=pending.operation_id,
                button=pending.button,
                accepted_frame=pending.accepted_frame,
                boundary_frame=self._completed.frame,
                boundary=self._completed.boundary,
                step_observations=tuple(pending.step_observations),
            )
        )
        self._completed = None
        self._pending = None

    def observe_text_event(self, kind: TextEventKind) -> None:
        """Track text-driven control domains without consuming their event journal."""
        if kind == TextEventKind.INPUT_REQUIRED:
            self._current_domain = _ControlDomain.IMMEDIATE
            self._complete(ControlBoundary.TEXT_INPUT_READY)
        elif kind == TextEventKind.SPECIAL_INTERFACE_OPENED:
            self._current_domain = _ControlDomain.IMMEDIATE
            self._complete(ControlBoundary.SPECIAL_INTERFACE_READY)
        elif kind == TextEventKind.MENU_CLOSED:
            pending = self._pending
            if (
                pending is not None
                and pending.input_domain == _ControlDomain.MENU
                and pending.accepted_frame is not None
            ):
                pending.input_domain = _ControlDomain.IMMEDIATE
            self._current_domain = _ControlDomain.IMMEDIATE
        elif kind in {
            TextEventKind.INPUT_RESOLVED,
            TextEventKind.MENU_OPENED,
            TextEventKind.SPECIAL_INTERFACE_CLOSED,
            TextEventKind.INTERACTION_CLOSED,
            TextEventKind.OVERWORLD_ENTERED,
            TextEventKind.BATTLE_ENDED,
        }:
            self._current_domain = _ControlDomain.IMMEDIATE

    def _signature_matches(self, hook: _Hook) -> bool:
        actual = bytes(
            self._pyboy.memory[
                hook.bank,
                hook.address : hook.address + len(hook.signature),
            ]
        )
        return actual == hook.signature

    def _build_callback(self, name: _HookName) -> Callable[[None], None]:
        def callback(_context: None) -> None:
            match name:
                case _HookName.OVERWORLD_INPUT:
                    self._observe_overworld_input()
                case _HookName.MENU_INPUT_ACCEPTED:
                    self._observe_accepted_input(_ControlDomain.MENU, _MENU_INPUT_ADDRESS)
                case _HookName.MENU_READY:
                    self._observe_ready(_ControlDomain.MENU, ControlBoundary.MENU_READY)
                case _HookName.NAMING_INPUT_ACCEPTED:
                    self._observe_accepted_input(_ControlDomain.NAMING, _JOY_PRESSED_ADDRESS)
                case _HookName.NAMING_READY:
                    self._observe_ready(_ControlDomain.NAMING, ControlBoundary.NAMING_READY)
                case _HookName.PLAYER_STEP_COMPLETED:
                    self._observe_player_step_completed()

        return callback

    def _observe_overworld_input(self) -> None:
        overworld_ready = self._is_overworld_ready()
        if overworld_ready:
            self._current_domain = _ControlDomain.OVERWORLD

        pending = self._pending
        if pending is None:
            return

        if pending.required_boundary is not None:
            if overworld_ready and self._pyboy.memory[_JOY_HELD_ADDRESS] == 0:
                self._complete(ControlBoundary.OVERWORLD_READY)
            return

        held = self._pyboy.memory[_JOY_HELD_ADDRESS]
        pressed = self._pyboy.memory[_JOY_PRESSED_ADDRESS]
        if pending.accepted_frame is None:
            if pending.input_domain == _ControlDomain.OVERWORLD and pressed & pending.button_mask:
                pending.accepted_frame = self._pyboy.frame_count
            return

        if overworld_ready and not held & pending.button_mask:
            self._complete(ControlBoundary.OVERWORLD_READY)

    def _observe_accepted_input(self, domain: _ControlDomain, input_address: int) -> None:
        """Record that the active input engine processed the requested button."""
        pending = self._pending
        if pending is None or pending.input_domain != domain or pending.accepted_frame is not None:
            return
        if self._pyboy.memory[input_address] & pending.button_mask:
            pending.accepted_frame = self._pyboy.frame_count

    def _observe_ready(self, domain: _ControlDomain, boundary: ControlBoundary) -> None:
        """Track and, when applicable, complete a prepared input boundary."""
        self._current_domain = domain
        pending = self._pending
        if pending is None:
            return
        if pending.required_boundary == boundary:
            if self._pyboy.memory[_JOY_HELD_ADDRESS] == 0:
                self._complete(boundary)
            return
        if pending.required_boundary is not None or pending.accepted_frame is None:
            return
        if self._pyboy.memory[_JOY_HELD_ADDRESS] & pending.button_mask:
            return
        self._complete(boundary)

    def _observe_immediate_input(self) -> None:
        """Fence bespoke screens after their next accepted and released input poll."""
        pending = self._pending
        if (
            pending is None
            or pending.required_boundary is not None
            or pending.input_domain != _ControlDomain.IMMEDIATE
            or self._completed is not None
        ):
            return

        frame = self._pyboy.frame_count
        if pending.accepted_frame is None:
            input_state = (
                self._pyboy.memory[_JOY_PRESSED_ADDRESS] | self._pyboy.memory[_MENU_INPUT_ADDRESS]
            )
            if input_state & pending.button_mask:
                pending.accepted_frame = frame
            return

        input_released = not self._pyboy.memory[_JOY_HELD_ADDRESS] & pending.button_mask
        input_poll_cleared = not self._pyboy.memory[_MENU_INPUT_ADDRESS] & pending.button_mask
        if pending.render_ready_frame is None:
            if input_released and input_poll_cleared:
                pending.render_ready_frame = frame + _RENDER_FENCE_FRAMES
            return
        if frame >= pending.render_ready_frame:
            self._complete(ControlBoundary.RENDER_READY)

    def _observe_player_step_completed(self) -> None:
        pending = self._pending
        if (
            pending is not None
            and pending.observe_steps
            and pending.accepted_frame is not None
            and self._pyboy.memory[_WALK_COUNTER_ADDRESS] == 0
        ):
            self._step_completed_this_tick = True

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
        if pending is None or pending.accepted_frame is None or self._completed is not None:
            return
        if pending.required_boundary is not None and pending.required_boundary != boundary:
            return
        self._completed = _CompletedOperation(
            boundary=boundary,
            frame=self._pyboy.frame_count,
        )
