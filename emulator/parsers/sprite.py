from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.schemas import Coords

_RANDOM_MOVEMENT = 0xFE
_NOT_RENDERED = 0xFF

_ITEM_BALL_ID = 0x69
_BOULDER_ID = 0x6B


class Sprite(BaseModel):
    """A sprite on the current map."""

    index: int
    coords: Coords
    is_rendered: bool
    moves_randomly: bool
    is_item_ball: bool
    is_boulder: bool

    model_config = ConfigDict(frozen=True)


def parse_sprites(mem: PyBoyMemoryView) -> dict[int, Sprite]:
    """
    Parse the list of sprites on the current map from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the sprites from.
    :return: A dictionary of normal sprites, keyed by index.
    """
    sprites = {}
    for i in range(0x10, 0xF0, 0x10):  # First sprite is the player.
        picture_id = mem[0xC100 + i]
        if picture_id == 0:  # No more sprites on this map.
            break
        index = i // 0x10
        sprites[index] = Sprite(
            index=index,
            # Sprite coordinates start counting from 4 for some reason.
            coords=Coords(row=mem[0xC204 + i] - 4, col=mem[0xC205 + i] - 4),
            is_rendered=mem[0xC102 + i] != _NOT_RENDERED,
            moves_randomly=mem[0xC206 + i] == _RANDOM_MOVEMENT,
            is_item_ball=picture_id == _ITEM_BALL_ID,
            is_boulder=picture_id == _BOULDER_ID,
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
        coords=Coords(row=mem[0xC2F4] - 4, col=mem[0xC2F5] - 4),
        is_rendered=mem[0xC1F2] != _NOT_RENDERED,
        moves_randomly=False,
        is_item_ball=False,
        is_boulder=False,
    )
