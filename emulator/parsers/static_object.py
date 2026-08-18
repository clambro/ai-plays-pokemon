"""Parser for supported coordinate-bound objects in Pokémon Yellow."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from common.enums import MapId
from common.schemas import Coords

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView

_OBJECT_TABLE_BANK = 0x3C
_OBJECT_MAPS_ADDRESS = 0x6A53
_MAP_RECORD_SIZE = 3
_OBJECT_RECORD_SIZE = 6
_TERMINATOR = 0xFF
_MAX_MAP_RECORDS = 0x100
_MAX_OBJECT_RECORDS = 0x100

# Bank and address pairs from the required Yellow Legacy ROM. The parser uses
# these only to decide which coordinate records are safe and useful to expose.
_SUPPORTED_HANDLERS = frozenset(
    {
        (0x07, 0x6547),  # PrintCinnabarQuiz
        (0x07, 0x66DF),  # BillsHousePC
        (0x11, 0x4629),  # Mansion1Script_Switches
        (0x14, 0x605C),  # Mansion2Script_Switches
        (0x14, 0x63F7),  # Mansion3Script_Switches
        (0x14, 0x659D),  # Mansion4Script_Switches
        (0x17, 0x5E43),  # OpenRedsPC
        (0x17, 0x60F3),  # GymTrashScript
        (0x18, 0x672D),  # OpenPokemonCenterPC
    }
)


class StaticObject(BaseModel):
    """A supported stationary object on one map."""

    index: int
    coords: Coords

    model_config = ConfigDict(frozen=True)


def parse_static_objects(
    mem: PyBoyMemoryView,
    map_id: MapId,
) -> dict[int, StaticObject]:
    """Parse supported coordinate-bound objects for a map.

    The returned identity is the object's original zero-based index in its ROM
    table. Unsupported entries are omitted without renumbering later objects.

    Args:
        mem: Current PyBoy memory view.
        map_id: Map whose object table should be read.

    Returns:
        Supported objects keyed by their stable map-local index.
    """
    table_address = _find_map_object_table(mem, map_id)
    if table_address is None:
        return {}

    objects = {}
    for index in range(_MAX_OBJECT_RECORDS):
        address = table_address + index * _OBJECT_RECORD_SIZE
        row = mem[_OBJECT_TABLE_BANK, address]
        if row == _TERMINATOR:
            break

        handler = (
            mem[_OBJECT_TABLE_BANK, address + 3],
            _read_word(mem, address + 4),
        )
        if handler in _SUPPORTED_HANDLERS:
            objects[index] = StaticObject(
                index=index,
                coords=Coords(
                    row=row,
                    col=mem[_OBJECT_TABLE_BANK, address + 1],
                ),
            )
    return objects


def _find_map_object_table(mem: PyBoyMemoryView, map_id: MapId) -> int | None:
    """Find a map's coordinate-bound object table in the ROM directory."""
    if map_id in {MapId.UNKNOWN, MapId.OUTSIDE}:
        return None

    for index in range(_MAX_MAP_RECORDS):
        address = _OBJECT_MAPS_ADDRESS + index * _MAP_RECORD_SIZE
        candidate_map_id = mem[_OBJECT_TABLE_BANK, address]
        if candidate_map_id == _TERMINATOR:
            return None
        if candidate_map_id == map_id:
            return _read_word(mem, address + 1)
    return None


def _read_word(mem: PyBoyMemoryView, address: int) -> int:
    """Read a little-endian word from the static-object ROM bank."""
    return mem[_OBJECT_TABLE_BANK, address] | mem[_OBJECT_TABLE_BANK, address + 1] << 8
