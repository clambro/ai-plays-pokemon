from enum import StrEnum


class OverworldTool(StrEnum):
    """An enum for the different overworld tools."""

    PRESS_BUTTONS = "press_buttons"
    NAVIGATION = "navigation"
    CRITIQUE = "critique"
    SOKOBAN_SOLVER = "sokoban_solver"
