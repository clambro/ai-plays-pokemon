"""Enumerations used by the text subflow."""

from enum import StrEnum


class TextHandler(StrEnum):
    """An enum for the different text handlers."""

    NAME = "name"
    DIALOG_BOX = "dialog_box"
    GENERIC = "generic"
