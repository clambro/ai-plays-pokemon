from enum import StrEnum


class Button(StrEnum):
    """The buttons that can be pressed in the game."""

    A = "a"
    B = "b"
    START = "start"
    SELECT = "select"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class FacingDirection(StrEnum):
    """The direction the player is facing."""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
