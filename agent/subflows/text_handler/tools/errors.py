"""Errors raised by deterministic text tools."""


class TextActionUnavailableError(Exception):
    """The requested text action is not valid for the current emulator state."""
