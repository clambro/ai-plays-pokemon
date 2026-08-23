"""Parser for sign data in Pokémon Yellow memory."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from common.schemas import Coords

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView


class Sign(BaseModel):
    """A sign on the current map."""

    index: int
    coords: Coords

    model_config = ConfigDict(frozen=True)


def parse_signs(mem: PyBoyMemoryView) -> dict[int, Sign]:
    """Parse signs on the current map from emulator memory.

    Args:
        mem: Current PyBoy memory view.

    Returns:
        Signs keyed by their map index.
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
