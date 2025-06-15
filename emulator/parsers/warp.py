from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.enums import MapId, WarpType


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
    warp_type: WarpType

    model_config = ConfigDict(frozen=True)


def parse_warps(mem: PyBoyMemoryView) -> dict[int, Warp]:
    """
    Parse the list of warps on the current map from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the warps from.
    :return: A dictionary of warps, keyed by index.
    """
    num_warps = mem[0xD3FB]
    warps: dict[int, Warp] = {}
    for i in range(num_warps):
        base = 0xD3FC + 4 * i
        y, x = mem[base], mem[base + 1]
        warps[i] = Warp(
            index=i,
            y=y,
            x=x,
            destination=MapId(mem[base + 3]),
            warp_type=_get_warp_type(y, x, warps),
        )
    return warps


def _get_warp_type(y: int, x: int, warps: dict[int, Warp]) -> WarpType:
    """
    Get the warp type for a warp at the given y and x coordinates, and update its twin in the
    collection if it exists.
    """
    for w in warps.values():
        if w.warp_type == WarpType.SINGLE and abs(w.y - y) + abs(w.x - x) == 1:
            warp_type = WarpType.DOUBLE_HORIZONTAL if w.y == y else WarpType.DOUBLE_VERTICAL
            warps[w.index] = Warp(
                index=w.index,
                y=w.y,
                x=w.x,
                destination=w.destination,
                warp_type=warp_type,
            )
            return warp_type
    return WarpType.SINGLE
