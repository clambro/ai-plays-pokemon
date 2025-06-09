from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.enums import MapId


class Warp(BaseModel):
    """
    A warp on the current map.

    Saving the destination is kinda cheating, but much easier than detecting a warp and going back
    to edit the memory.
    """

    index: int
    y: int
    x: int
    destination: MapId

    model_config = ConfigDict(frozen=True)


def parse_warps(mem: PyBoyMemoryView) -> dict[int, Warp]:
    """
    Parse the list of warps on the current map from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the warps from.
    :return: A dictionary of warps, keyed by index.
    """
    num_warps = mem[0xD3FB]
    warps = {}
    for i in range(num_warps):
        base = 0xD3FC + 4 * i
        warps[i] = Warp(
            index=i,
            y=mem[base],
            x=mem[base + 1],
            destination=MapId(mem[base + 3]),
        )
    return warps
