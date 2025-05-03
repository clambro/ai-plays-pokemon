from enum import StrEnum


class Button(StrEnum):
    """
    The buttons that can be pressed in the game.

    The select button has no real purpose to the AI, so we exclude it to avoid confusion.
    """

    A = "a"
    B = "b"
    START = "start"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
