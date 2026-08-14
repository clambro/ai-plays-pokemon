"""Parse semantic text events from the required Yellow Legacy ROM."""

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from emulator.parsers.screen_text import INT_TO_CHAR_MAP
from emulator.text_events import DialogPage, TextEventJournal, TextEventKind

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyboy import PyBoy, PyBoyMemoryView


class _HookName(StrEnum):
    """Semantic execution points in the ROM text engine."""

    TEXT_PROCESSOR = auto()
    TEXT_COMMAND = auto()
    CONTINUE_WITHOUT_PAUSE = auto()
    AUTOMATIC_SCROLL = auto()
    WAIT_LOOP = auto()
    WAIT_EXIT = auto()
    MENU_INPUT = auto()
    MENU_EXIT = auto()
    MENU_TIMEOUT = auto()
    SPECIAL_INTERFACE_WAIT = auto()
    SPECIAL_INTERFACE_EXIT = auto()
    TEXT_DISPLAY_CLOSED = auto()
    OVERWORLD_ENTERED = auto()
    BATTLE_ENDED = auto()


@dataclass(frozen=True, slots=True, kw_only=True)
class _Hook:
    """One executable address and its required instruction signature."""

    name: _HookName
    bank: int
    address: int
    signature: bytes


# Addresses and signatures from the required Yellow Legacy ROM build. Validate every location
# before installing any breakpoint because a hook at the wrong executable address corrupts play.
_HOOKS = (
    _Hook(
        name=_HookName.TEXT_PROCESSOR,
        bank=0x00,
        address=0x1925,  # TextCommandProcessor
        signature=bytes.fromhex("fa a5 d3 f5 cb cf"),
    ),
    _Hook(
        name=_HookName.TEXT_COMMAND,
        bank=0x00,
        address=0x193A,  # NextTextCommand
        signature=bytes.fromhex("2a fe 50 20 05 f1"),
    ),
    _Hook(
        name=_HookName.CONTINUE_WITHOUT_PAUSE,
        bank=0x00,
        address=0x18EF,  # _ContTextNoPause
        signature=bytes.fromhex("d5 cd fd 18 cd fd"),
    ),
    _Hook(
        name=_HookName.AUTOMATIC_SCROLL,
        bank=0x00,
        address=0x19CC,  # TextCommand_SCROLL
        signature=bytes.fromhex("3e 7f ea f2 c4 cd"),
    ),
    _Hook(
        name=_HookName.WAIT_LOOP,
        bank=0x00,
        address=0x386C,  # WaitForTextScrollButtonPress.loop
        signature=bytes.fromhex("e5 fa 9a d0 a7 28"),
    ),
    _Hook(
        name=_HookName.WAIT_EXIT,
        bank=0x00,
        address=0x3898,  # WaitForTextScrollButtonPress return
        signature=bytes.fromhex("c9 fa 2a d1 fe 04"),
    ),
    _Hook(
        name=_HookName.MENU_INPUT,
        bank=0x00,
        address=0x3AB6,  # HandleMenuInput_
        signature=bytes.fromhex("f0 8b f5 f0 8c f5"),
    ),
    _Hook(
        name=_HookName.MENU_TIMEOUT,
        bank=0x00,
        address=0x3AF3,  # HandleMenuInput_.giveUpWaiting
        signature=bytes.fromhex("f1 e0 8c f1 e0 8b"),
    ),
    _Hook(
        name=_HookName.MENU_EXIT,
        bank=0x00,
        address=0x3B5D,  # HandleMenuInput_.skipPlayingSound
        signature=bytes.fromhex("f1 e0 8c f1 e0 8b"),
    ),
    _Hook(
        name=_HookName.TEXT_DISPLAY_CLOSED,
        bank=0x00,
        address=0x284F,  # Completed CloseTextDisplay path
        signature=bytes.fromhex("c3 b9 22 e5 21 75"),
    ),
    _Hook(
        name=_HookName.BATTLE_ENDED,
        bank=0x04,
        address=0x7CA1,  # EndOfBattle.resetVariables
        signature=bytes.fromhex("af ea 82 d0 ea 2a"),
    ),
    _Hook(
        name=_HookName.OVERWORLD_ENTERED,
        bank=0x00,
        address=0x0238,  # EnterMap completed
        signature=bytes.fromhex("af ea 6b cd cd 05"),
    ),
    _Hook(
        name=_HookName.SPECIAL_INTERFACE_WAIT,
        bank=0x10,
        address=0x434A,  # ShowPokedexDataInternal.waitForButtonPress
        signature=bytes.fromhex("cd 2b 38 f0 b5 e6"),
    ),
    _Hook(
        name=_HookName.SPECIAL_INTERFACE_EXIT,
        bank=0x10,
        address=0x4353,  # ShowPokedexDataInternal wait completed
        signature=bytes.fromhex("f1 e0 d7 cd f7 3d"),
    ),
)

_TX_END = 0x50

_TILE_MAP_START = 0xC3A0
_TILE_MAP_WIDTH = 20
_WINDOW_Y_ADDRESS = 0xFF4A
_SCREEN_HEIGHT_PIXELS = 144
_AUDIO_FADE_FLAGS_ADDRESS = 0xD72B  # wd72c
_REDUCED_VOLUME_INTERFACE_FLAG = 1 << 1

_TOP_BORDER_ROW = 12
_TOP_TEXT_ROW = 14
_BOTTOM_TEXT_ROW = 16
_BOTTOM_BORDER_ROW = 17

_TOP_LEFT_BORDER = 0x79
_HORIZONTAL_BORDER = 0x7A
_TOP_RIGHT_BORDER = 0x7B
_VERTICAL_BORDER = 0x7C
_BOTTOM_LEFT_BORDER = 0x7D
_BOTTOM_RIGHT_BORDER = 0x7E
_CURSOR = 0xEE


class RomTextRecorder:
    """Translate ROM text-engine execution into ordered semantic events."""

    def __init__(
        self,
        pyboy: PyBoy,
        journal: TextEventJournal,
        on_event: Callable[[TextEventKind], None] | None = None,
    ) -> None:
        """Keep the owner-thread emulator and its transient event journal."""
        self._pyboy = pyboy
        self._journal = journal
        self._on_event = on_event
        self._text_processor_depth = 0
        self._inside_wait = False

    def install(self) -> None:
        """Validate the required ROM layout and register every text hook."""
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
            self._handle(name)

        return callback

    def _handle(self, name: _HookName) -> None:
        if name in {_HookName.TEXT_PROCESSOR, _HookName.TEXT_COMMAND}:
            self._handle_text_processor(name)
            return
        if name in {
            _HookName.MENU_INPUT,
            _HookName.MENU_EXIT,
            _HookName.MENU_TIMEOUT,
            _HookName.SPECIAL_INTERFACE_WAIT,
            _HookName.SPECIAL_INTERFACE_EXIT,
        }:
            self._handle_interface(name)
            return
        match name:
            case _HookName.CONTINUE_WITHOUT_PAUSE | _HookName.AUTOMATIC_SCROLL:
                self._record_page(TextEventKind.AUTOMATIC_SCROLL)
            case _HookName.WAIT_LOOP:
                self._record_wait_entry()
            case _HookName.WAIT_EXIT:
                self._record_wait_exit()
            case _HookName.TEXT_DISPLAY_CLOSED:
                self._record(TextEventKind.INTERACTION_CLOSED)
            case _HookName.OVERWORLD_ENTERED:
                self._record(TextEventKind.OVERWORLD_ENTERED)
            case _HookName.BATTLE_ENDED:
                self._record(TextEventKind.BATTLE_ENDED)

    def _handle_text_processor(self, name: _HookName) -> None:
        if name == _HookName.TEXT_PROCESSOR:
            self._text_processor_depth += 1
            return
        if self._pyboy.memory[self._pyboy.register_file.HL] != _TX_END:
            return
        if self._text_processor_depth <= 1:
            self._record_page(TextEventKind.PAGE_COMPLETED)
        self._text_processor_depth = max(0, self._text_processor_depth - 1)

    def _handle_interface(self, name: _HookName) -> None:
        kind = {
            _HookName.MENU_INPUT: TextEventKind.MENU_OPENED,
            _HookName.MENU_EXIT: TextEventKind.MENU_CLOSED,
            _HookName.MENU_TIMEOUT: TextEventKind.MENU_CLOSED,
            _HookName.SPECIAL_INTERFACE_WAIT: TextEventKind.SPECIAL_INTERFACE_OPENED,
            _HookName.SPECIAL_INTERFACE_EXIT: TextEventKind.SPECIAL_INTERFACE_CLOSED,
        }[name]
        page = (
            _decode_standard_dialog_page(self._pyboy.memory)
            if name == _HookName.MENU_INPUT
            else None
        )
        self._record(kind, page=page)

    def _record_page(self, kind: TextEventKind) -> None:
        if page := _decode_standard_dialog_page(self._pyboy.memory):
            self._record(kind, page=page)

    def _record_wait_entry(self) -> None:
        if self._inside_wait:
            return
        self._inside_wait = True
        page = _decode_standard_dialog_page(self._pyboy.memory)
        if page is not None:
            self._record(TextEventKind.INPUT_REQUIRED, page=page)
        elif self._is_reduced_volume_interface_open():
            self._record(TextEventKind.SPECIAL_INTERFACE_OPENED)

    def _record_wait_exit(self) -> None:
        page = _decode_standard_dialog_page(self._pyboy.memory)
        if self._inside_wait or page is not None:
            self._record(TextEventKind.INPUT_RESOLVED, page=page)
        if page is None and self._is_reduced_volume_interface_open():
            self._record(TextEventKind.SPECIAL_INTERFACE_CLOSED)
        self._inside_wait = False

    def _is_reduced_volume_interface_open(self) -> bool:
        return bool(self._pyboy.memory[_AUDIO_FADE_FLAGS_ADDRESS] & _REDUCED_VOLUME_INTERFACE_FLAG)

    def _record(self, kind: TextEventKind, *, page: DialogPage | None = None) -> None:
        event = self._journal.append(
            frame=self._pyboy.frame_count,
            kind=kind,
            page=page,
        )
        if event is not None and self._on_event is not None:
            self._on_event(kind)


def _decode_standard_dialog_page(mem: PyBoyMemoryView) -> DialogPage | None:
    """Copy a standard dialog page from WRAM at a semantic hook boundary."""
    if mem[_WINDOW_Y_ADDRESS] >= _SCREEN_HEIGHT_PIXELS:
        return None

    tiles = mem[
        _TILE_MAP_START + _TOP_BORDER_ROW * _TILE_MAP_WIDTH : _TILE_MAP_START
        + (_BOTTOM_BORDER_ROW + 1) * _TILE_MAP_WIDTH
    ]
    rows = [
        tiles[offset : offset + _TILE_MAP_WIDTH] for offset in range(0, len(tiles), _TILE_MAP_WIDTH)
    ]
    if not _has_standard_dialog_border(rows):
        return None

    top_line = _decode_line(rows[_TOP_TEXT_ROW - _TOP_BORDER_ROW][1:-1])
    bottom_line = _decode_line(rows[_BOTTOM_TEXT_ROW - _TOP_BORDER_ROW][1:-1])
    if not top_line and not bottom_line:
        return None
    return DialogPage(top_line=top_line, bottom_line=bottom_line)


def _has_standard_dialog_border(rows: list[list[int]]) -> bool:
    top = rows[0]
    bottom = rows[-1]
    return (
        len(rows) == _BOTTOM_BORDER_ROW - _TOP_BORDER_ROW + 1
        and all(len(row) == _TILE_MAP_WIDTH for row in rows)
        and top[0] == _TOP_LEFT_BORDER
        and top[-1] == _TOP_RIGHT_BORDER
        and all(tile == _HORIZONTAL_BORDER for tile in top[1:-1])
        and bottom[0] == _BOTTOM_LEFT_BORDER
        and bottom[-1] == _BOTTOM_RIGHT_BORDER
        and all(tile == _HORIZONTAL_BORDER for tile in bottom[1:-1])
        and all(row[0] == _VERTICAL_BORDER and row[-1] == _VERTICAL_BORDER for row in rows[1:-1])
    )


def _decode_line(tiles: list[int]) -> str:
    return "".join(
        " " if tile == _CURSOR else INT_TO_CHAR_MAP.get(tile, " ") for tile in tiles
    ).strip()
