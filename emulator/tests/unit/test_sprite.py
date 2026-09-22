"""Sprite presence follows ROM object flags independently of rendering."""

from typing import TYPE_CHECKING, cast

import pytest

from emulator.parsers.sprite import parse_sprites

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView


@pytest.mark.unit
@pytest.mark.parametrize("flag_index", [0, 7, 8, 255])
def test_sprite_appearance_and_disappearance(flag_index: int) -> None:
    """Hidden sprites stay absent regardless of rendering; offscreen NPCs remain present."""
    mem = bytearray(0x10000)
    mem[0xD61B:0xD61E] = bytes([2, flag_index, 0xFF])
    for offset in (0x10, 0x20):
        mem[0xC100 + offset] = 0x16
        mem[0xC102 + offset] = 0xFF
        mem[0xC204 + offset] = 4
        mem[0xC205 + offset] = 4
    memory = cast("PyBoyMemoryView", mem)
    flag_address = 0xD5F3 + flag_index // 8
    flag_mask = 1 << (flag_index % 8)

    sprites = parse_sprites(memory)
    assert set(sprites) == {1, 2}
    assert not sprites[2].is_rendered

    mem[flag_address] |= flag_mask
    sprites = parse_sprites(memory)
    assert set(sprites) == {1}

    mem[0xC122] = 0
    assert set(parse_sprites(memory)) == {1}

    mem[flag_address] &= ~flag_mask
    assert set(parse_sprites(memory)) == {1, 2}
