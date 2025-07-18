from enum import StrEnum


class OverworldTool(StrEnum):
    """An enum for the different overworld tools."""

    PRESS_BUTTONS = "press_buttons"
    NAVIGATION = "navigation"
    SWAP_FIRST_POKEMON = "swap_first_pokemon"
    SOKOBAN_SOLVER = "sokoban_solver"
    CRITIQUE = "critique"
