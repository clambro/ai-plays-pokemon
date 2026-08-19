"""ROM-backed tests for supported coordinate-bound objects."""

from typing import TYPE_CHECKING

import pytest
from pyboy import PyBoy

from common.constants import DEFAULT_ROM_PATH
from common.enums import FacingDirection, MapId
from common.schemas import Coords
from emulator.parsers.static_object import parse_static_objects

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pyboy import PyBoyMemoryView


@pytest.fixture(scope="module")
def rom_memory() -> Iterator[PyBoyMemoryView]:
    """Provide the required Yellow Legacy ROM through PyBoy's banked memory view."""
    pyboy = PyBoy(DEFAULT_ROM_PATH, sound_volume=0, window="null")
    try:
        yield pyboy.memory
    finally:
        pyboy.stop()


@pytest.mark.integration
def test_parse_bills_computer(rom_memory: PyBoyMemoryView) -> None:
    """Decode a known supported object from the ROM table."""
    objects = parse_static_objects(rom_memory, MapId.BILLS_HOUSE)

    assert set(objects) == {0}
    assert objects[0].coords == Coords(row=4, col=1)
    assert objects[0].interaction_direction == FacingDirection.UP


@pytest.mark.integration
def test_parse_all_vermilion_gym_puzzle_cans(
    rom_memory: PyBoyMemoryView,
) -> None:
    """Keep all fifteen puzzle cans distinct while excluding earlier scenery entries."""
    objects = parse_static_objects(rom_memory, MapId.VERMILION_GYM)
    expected_indices = set(range(3, 18))

    assert set(objects) == expected_indices
    assert len({entity.coords for entity in objects.values()}) == len(expected_indices)
    assert all(entity.interaction_direction is None for entity in objects.values())


@pytest.mark.integration
def test_exclude_game_corner_handlers(rom_memory: PyBoyMemoryView) -> None:
    """Do not expose the Game Corner's slot machines and hidden coins."""
    assert parse_static_objects(rom_memory, MapId.GAME_CORNER) == {}
