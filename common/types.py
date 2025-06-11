from collections.abc import Callable

from emulator.game_state import YellowLegacyGameState

# Useful shorthand for a common string builder type.
StateStringBuilderT = Callable[[YellowLegacyGameState], str]
