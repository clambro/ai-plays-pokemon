from typing import Callable

from emulator.game_state import YellowLegacyGameState

# Useful shorthand for a common string builder type.
StateStringBuilder = Callable[[YellowLegacyGameState], str]
