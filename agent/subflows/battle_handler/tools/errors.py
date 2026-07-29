"""Errors raised by deterministic battle tools."""


class BattleActionUnavailableError(Exception):
    """The requested battle action is not valid for the current emulator state."""
