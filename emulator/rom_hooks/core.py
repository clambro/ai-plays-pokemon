"""Shared registration for validated ROM execution hooks."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyboy import PyBoy


@dataclass(frozen=True, slots=True, kw_only=True)
class RomHook[NameT]:
    """One executable address and its required instruction signature."""

    name: NameT
    bank: int
    address: int
    signature: bytes


def install_hooks[NameT](
    pyboy: PyBoy,
    hooks: tuple[RomHook[NameT], ...],
    handler: Callable[[NameT], None],
) -> None:
    """Validate a complete hook group before registering its callbacks."""
    mismatch = next((hook for hook in hooks if not _signature_matches(pyboy, hook)), None)
    if mismatch is not None:
        raise RuntimeError(f"Required ROM instruction signature does not match at {mismatch.name}.")

    for hook in hooks:
        pyboy.hook_register(
            hook.bank,
            hook.address,
            _build_callback(handler, hook.name),
            None,
        )


def _signature_matches[NameT](pyboy: PyBoy, hook: RomHook[NameT]) -> bool:
    actual = bytes(
        pyboy.memory[
            hook.bank,
            hook.address : hook.address + len(hook.signature),
        ]
    )
    return actual == hook.signature


def _build_callback[NameT](
    handler: Callable[[NameT], None],
    name: NameT,
) -> Callable[[None], None]:
    def callback(_context: None) -> None:
        handler(name)

    return callback
