from random import random

from agent.decorators import named_action
from agent.state import AgentState
from emulator.context import get_emulator
from emulator.enums import Button


@named_action(reads=[], writes=[])
async def press_random_button(state: AgentState) -> None:
    """Press a random button for testing purposes."""
    emulator = get_emulator()
    if not emulator:
        raise RuntimeError("No emulator instance available in the current context")

    button: Button = random.choice(list(Button))
    await emulator.press_buttons([button])
