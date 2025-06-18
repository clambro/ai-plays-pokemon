from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.schemas import Coords


class Sign(BaseModel):
    """A sign on the current map."""

    index: int
    coords: Coords

    model_config = ConfigDict(frozen=True)


def parse_signs(mem: PyBoyMemoryView) -> dict[int, Sign]:
    """
    Parse the list of signs on the current map from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the signs from.
    :return: A dictionary of signs, keyed by index.
    """
    num_signs = mem[0xD4FD]
    signs = {}
    for i in range(num_signs):
        base = 0xD4FE + 2 * i
        signs[i] = Sign(
            index=i,
            coords=Coords(row=mem[base], col=mem[base + 1]),
        )
    return signs
