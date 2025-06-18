from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.enums import MapId, WarpType
from common.schemas import Coords


class Warp(BaseModel):
    """
    A warp on the current map.

    Saving the destination is kinda cheating, but much easier than detecting a warp and going back
    to edit the memory.
    """

    index: int
    coords: Coords
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
        coords = Coords(row=mem[base], col=mem[base + 1])
        warps[i] = Warp(
            index=i,
            coords=coords,
            destination=MapId(mem[base + 3]),
            warp_type=_get_warp_type(coords, warps),
        )
    return warps


def _get_warp_type(coords: Coords, warps: dict[int, Warp]) -> WarpType:
    """
    Get the warp type for a warp at the given coordinates, and update its twin in the collection
    if it exists.
    """
    for w in warps.values():
        if w.warp_type == WarpType.SINGLE and (w.coords - coords).length == 1:
            warp_type = (
                WarpType.DOUBLE_HORIZONTAL
                if w.coords.row == coords.row
                else WarpType.DOUBLE_VERTICAL
            )
            warps[w.index] = Warp(
                index=w.index,
                coords=w.coords,
                destination=w.destination,
                warp_type=warp_type,
            )
            return warp_type
    return WarpType.SINGLE
