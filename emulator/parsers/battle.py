from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict


class Battle(BaseModel):
    """The state of the current battle."""

    is_in_battle: bool

    model_config = ConfigDict(frozen=True)


def parse_battle_state(mem: PyBoyMemoryView) -> Battle:
    """
    Create a new battle state from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the battle state from.
    :return: A new battle state.
    """
    return Battle(is_in_battle=bool(mem[0xD057]))
