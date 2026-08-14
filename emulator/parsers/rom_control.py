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
    """Executable boundaries used by overworld control coordination."""

    OVERWORLD_INPUT = auto()
    MENU_READY = auto()
    PLAYER_STEP_COMPLETED = auto()


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
    overworld_only: bool = False
    observe_steps: bool = False
    accepted_frame: int | None = None
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
        name=_HookName.MENU_READY,
        bank=0x00,
        address=0x3ACD,  # HandleMenuInput_.loop2, after PlaceMenuCursor and Delay3
        signature=bytes.fromhex("e5 fa 9a d0 a7 28"),
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
_OVERWORLD_FLAGS_ADDRESS = 0xCD60

_SUPPRESSED_OR_SIMULATED_INPUT = (1 << 0) | (1 << 5) | (1 << 7)
_DOOR_LEDGE_OR_SPINNER_MOVEMENT = (1 << 1) | (1 << 6) | (1 << 7)
_BOULDER_MOVING = 1 << 1


class RomControlRecorder:
    """Correlate an injected overworld button with the ROM's next ready boundary."""

    def __init__(self, pyboy: PyBoy, results: ControlResultWaiter) -> None:
        """Keep the owner-thread emulator and asynchronous result handoff."""
        self._pyboy = pyboy
        self._results = results
        self._next_operation_id = 1
        self._pending: _PendingOperation | None = None
        self._completed: _CompletedOperation | None = None
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

    def arm(self, button: Button, *, observe_steps: bool = False) -> int:
        """Arm one operation before its button pulse is scheduled."""
        if self._pending is not None:
            raise RuntimeError("A control operation is already pending.")
        operation_id = self._next_operation_id
        self._next_operation_id += 1
        self._pending = _PendingOperation(
            operation_id=operation_id,
            button=button,
            button_mask=_BUTTON_MASKS[button],
            observe_steps=observe_steps,
        )
        return operation_id

    def arm_overworld_resume(self) -> int:
        """Wait for overworld control after an already-active scripted interaction."""
        if self._pending is not None:
            raise RuntimeError("A control operation is already pending.")
        operation_id = self._next_operation_id
        self._next_operation_id += 1
        self._pending = _PendingOperation(
            operation_id=operation_id,
            button=None,
            button_mask=0,
            overworld_only=True,
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

        if self._completed is None:
            return
        if pending is None or pending.accepted_frame is None:
            raise RuntimeError("Completed control operation has no pending input.")
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
        """Complete accepted overworld input when standard text awaits input."""
        if kind == TextEventKind.INPUT_REQUIRED and not (
            self._pending is not None and self._pending.overworld_only
        ):
            self._complete(ControlBoundary.TEXT_INPUT_READY)

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
            if name == _HookName.OVERWORLD_INPUT:
                self._observe_overworld_input()
            elif name == _HookName.MENU_READY:
                self._observe_menu_ready()
            else:
                self._observe_player_step_completed()

        return callback

    def _observe_overworld_input(self) -> None:
        pending = self._pending
        if pending is None:
            return

        if pending.overworld_only:
            if self._is_overworld_ready():
                self._complete(ControlBoundary.OVERWORLD_READY)
            return

        held = self._pyboy.memory[_JOY_HELD_ADDRESS]
        pressed = self._pyboy.memory[_JOY_PRESSED_ADDRESS]
        if pending.accepted_frame is None:
            if pressed & pending.button_mask:
                pending.accepted_frame = self._pyboy.frame_count
            return

        if self._is_overworld_ready() and not held & pending.button_mask:
            self._complete(ControlBoundary.OVERWORLD_READY)

    def _observe_menu_ready(self) -> None:
        pending = self._pending
        if pending is None or pending.overworld_only or pending.accepted_frame is None:
            return
        if self._pyboy.memory[_JOY_HELD_ADDRESS] & pending.button_mask:
            return
        self._complete(ControlBoundary.MENU_READY)

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
        self._completed = _CompletedOperation(
            boundary=boundary,
            frame=self._pyboy.frame_count,
        )
