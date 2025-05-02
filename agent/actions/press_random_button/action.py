from random import random

from burr.core.action import action
from agent.state import AgentState
from emulator.context import get_emulator
from emulator.enums import Button


PRESS_RANDOM_BUTTON = "Press Random Button"


@action(reads=[], writes=[])
async def press_random_button(state: AgentState) -> AgentState:
    """Press a random button for testing purposes."""
    emulator = get_emulator()
    if not emulator:
        raise RuntimeError("No emulator instance available in the current context")

    button: Button = random.choice(list(Button))
    print(button)
    await emulator.press_buttons([button])
    return state
