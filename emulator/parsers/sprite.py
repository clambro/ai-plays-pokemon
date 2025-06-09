from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict


class Sprite(BaseModel):
    """A sprite on the current map."""

    index: int
    y: int
    x: int
    is_rendered: bool
    moves_randomly: bool

    model_config = ConfigDict(frozen=True)


def parse_sprites(mem: PyBoyMemoryView) -> dict[int, Sprite]:
    """
    Parse the list of sprites on the current map from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the sprites from.
    :return: A dictionary of normal sprites, keyed by index.
    """
    sprites = {}
    for i in range(0x10, 0xF0, 0x10):  # First sprite is the player.
        if mem[0xC100 + i] == 0:  # No more sprites on this map.
            break
        index = i // 0x10
        sprites[index] = Sprite(
            index=index,
            # Sprite coordinates start counting from 4 for some reason.
            y=mem[0xC204 + i] - 4,
            x=mem[0xC205 + i] - 4,
            is_rendered=mem[0xC102 + i] != 0xFF,
            moves_randomly=mem[0xC206 + i] == 0xFE,
        )
    return sprites


def parse_pikachu_sprite(mem: PyBoyMemoryView) -> Sprite:
    """
    Parse the pikachu sprite from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the pikachu sprite from.
    :return: The pikachu sprite.
    """
    return Sprite(
        index=15,
        # Sprite coordinates start counting from 4 for some reason.
        y=mem[0xC2F4] - 4,
        x=mem[0xC2F5] - 4,
        is_rendered=mem[0xC1F2] != 0xFF,
        moves_randomly=False,
    )
