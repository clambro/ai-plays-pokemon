import asyncio
import random

from burr.core.action import action
from agent.state import AgentState
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button


PRESS_RANDOM_BUTTON = "Press Random Button"


@action.pydantic(reads=[], writes=[])
async def press_random_button(state: AgentState) -> AgentState:
    """Press a random button for testing purposes."""
    await asyncio.sleep(random.uniform(0, 3))  # Pretend to do something.
    button: Button = random.choice(list(Button))
    await YellowLegacyEmulator.press_buttons([button])
    return state
