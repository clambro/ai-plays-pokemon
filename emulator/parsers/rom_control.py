"""Observe control boundaries in the required Yellow Legacy ROM."""

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from common.enums import Button
from emulator.control_events import ControlBoundary, ControlResult, ControlResultWaiter
from emulator.text_events import TextEventKind

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyboy import PyBoy


class _HookName(StrEnum):
    """Executable boundaries used by overworld control coordination."""

    OVERWORLD_INPUT = auto()
    MENU_READY = auto()


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
    button: Button
    button_mask: int
    accepted_frame: int | None = None


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
_JOY_PRESSED_ADDRESS = 0xFFB3
_JOY_HELD_ADDRESS = 0xFFB4

_NPC_OR_IGNORED_OR_SIMULATED_INPUT = (1 << 0) | (1 << 5) | (1 << 7)
_DOOR_LEDGE_OR_SPINNER_MOVEMENT = (1 << 1) | (1 << 6) | (1 << 7)


class RomControlRecorder:
    """Correlate an injected overworld button with the ROM's next ready boundary."""

    def __init__(self, pyboy: PyBoy, results: ControlResultWaiter) -> None:
        """Keep the owner-thread emulator and asynchronous result handoff."""
        self._pyboy = pyboy
        self._results = results
        self._next_operation_id = 1
        self._pending: _PendingOperation | None = None
        self._completed: ControlResult | None = None

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

    def arm(self, button: Button) -> int:
        """Arm one operation before its button pulse is scheduled."""
        if self._pending is not None:
            raise RuntimeError("A control operation is already pending.")
        operation_id = self._next_operation_id
        self._next_operation_id += 1
        self._pending = _PendingOperation(
            operation_id=operation_id,
            button=button,
            button_mask=_BUTTON_MASKS[button],
        )
        return operation_id

    def publish_tick(self) -> None:
        """Publish a completed operation after its containing tick has rendered."""
        if self._completed is None:
            return
        self._results.publish(self._completed)
        self._completed = None
        self._pending = None

    def observe_text_event(self, kind: TextEventKind) -> None:
        """Complete accepted overworld input when standard text awaits input."""
        if kind == TextEventKind.INPUT_REQUIRED:
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
            else:
                self._observe_menu_ready()

        return callback

    def _observe_overworld_input(self) -> None:
        pending = self._pending
        if pending is None:
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
        if pending is None or pending.accepted_frame is None:
            return
        if self._pyboy.memory[_JOY_HELD_ADDRESS] & pending.button_mask:
            return
        self._complete(ControlBoundary.MENU_READY)

    def _is_overworld_ready(self) -> bool:
        mem = self._pyboy.memory
        return (
            mem[_WALK_COUNTER_ADDRESS] == 0
            and mem[_JOY_IGNORE_ADDRESS] == 0
            and not mem[_JOYPAD_STATE_ADDRESS] & _NPC_OR_IGNORED_OR_SIMULATED_INPUT
            and not mem[_MOVEMENT_STATE_ADDRESS] & _DOOR_LEDGE_OR_SPINNER_MOVEMENT
            and mem[_NPC_MOVEMENT_SCRIPT_ADDRESS] == 0
            and mem[_BATTLE_STATE_ADDRESS] == 0
            and mem[_CURRENT_OPPONENT_ADDRESS] == 0
        )

    def _complete(self, boundary: ControlBoundary) -> None:
        pending = self._pending
        if pending is None or pending.accepted_frame is None or self._completed is not None:
            return
        self._completed = ControlResult(
            operation_id=pending.operation_id,
            button=pending.button,
            accepted_frame=pending.accepted_frame,
            boundary_frame=self._pyboy.frame_count,
            boundary=boundary,
        )
