from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.schemas import Coords

_RANDOM_MOVEMENT = 0xFE
_NOT_RENDERED = 0xFF


class Sprite(BaseModel):
    """A sprite on the current map."""

    index: int
    name: str
    coords: Coords
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
        picture_id = mem[0xC100 + i]
        if picture_id == 0:  # No more sprites on this map.
            break
        index = i // 0x10
        sprites[index] = Sprite(
            index=index,
            name=_ID_TO_SPRITE_NAME.get(picture_id, "UNKNOWN"),
            # Sprite coordinates start counting from 4 for some reason.
            coords=Coords(row=mem[0xC204 + i] - 4, col=mem[0xC205 + i] - 4),
            is_rendered=mem[0xC102 + i] != _NOT_RENDERED,
            moves_randomly=mem[0xC206 + i] == _RANDOM_MOVEMENT,
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
        name="PIKACHU",
        # Sprite coordinates start counting from 4 for some reason.
        coords=Coords(row=mem[0xC2F4] - 4, col=mem[0xC2F5] - 4),
        is_rendered=mem[0xC1F2] != _NOT_RENDERED,
        moves_randomly=False,
    )


_ID_TO_SPRITE_NAME = {
    # Zero is the null sprite indicating the end of the sprite list.
    # One is the player sprite, which will never be parsed as a sprite.
    0x02: "RIVAL",
    0x03: "PROFESSOR OAK",
    0x04: "YOUNGSTER",
    0x05: "MONSTER",
    0x06: "COOLTRAINER ♀",
    0x07: "COOLTRAINER ♂",
    0x08: "LITTLE GIRL",
    0x09: "BIRD",
    0x0A: "MIDDLE AGED MAN",
    0x0B: "GAMBLER",
    0x0C: "SUPER NERD",
    0x0D: "GIRL",
    0x0E: "HIKER",
    0x0F: "BEAUTY",
    0x10: "GENTLEMAN",
    0x11: "DAISY",
    0x12: "BIKER",
    0x13: "SAILOR",
    0x14: "COOK",
    0x15: "BIKE SHOP CLERK",
    0x16: "MR FUJI",
    0x17: "GIOVANNI",
    0x18: "ROCKET",
    0x19: "CHANNELER",
    0x1A: "WAITER",
    0x1B: "SILPH WORKER ♀",
    0x1C: "MIDDLE AGED WOMAN",
    0x1D: "BRUNETTE GIRL",
    0x1E: "LANCE",
    # 1F is an unused alternate player sprite.
    0x20: "SCIENTIST",
    0x21: "ROCKER",
    0x22: "SWIMMER",
    0x23: "SAFARI ZONE WORKER",
    0x24: "GYM GUIDE",
    0x25: "OLD MAN",
    0x26: "CLERK",
    0x27: "FISHING GURU",
    0x28: "OLD WOMAN",
    0x29: "NURSE",
    0x2A: "LINK RECEPTIONIST",
    0x2B: "SILPH PRESIDENT",
    0x2C: "SILPH WORKER ♂",
    0x2D: "WARDEN",
    0x2E: "CAPTAIN",
    0x2F: "FISHER",
    0x30: "KOGA",
    0x31: "GUARD",
    # 32 is an unused alternate player sprite.
    0x33: "MOM",
    0x34: "BALDING GUY",
    0x35: "LITTLE BOY",
    # 36 is an unused alternate player sprite.
    0x37: "GAMEBOY KID",
    0x38: "CLEFAIRY",
    0x39: "AGATHA",
    0x3A: "BRUNO",
    0x3B: "LORELEI",
    0x3C: "SURFING SEEL",
    0x3D: "PIKACHU",
    0x3E: "OFFICER JENNY",
    0x3F: "SANDSHREW",
    0x40: "ODDISH",
    0x41: "BULBASAUR",
    0x42: "JIGGLYPUFF",
    0x43: "CLEFAIRY",  # Slightly different from the other Clefairy, but doesn't matter here.
    0x44: "CHANSEY",
    0x45: "JESSIE",
    0x46: "JAMES",
    0x47: "BROCK",
    0x48: "MISTY",
    0x49: "SURGE",
    0x4A: "ERIKA",
    0x4B: "SABRINA",
    0x4C: "BLAINE",
    0x4D: "JANINE",
    0x4E: "ARTICUNO",
    0x4F: "MOLTRES",
    0x50: "ZAPDOS",
    0x51: "MR MIME",
    0x52: "MEWTWO",
    0x53: "MEW",
    0x54: "KRIS",
    0x55: "KABUTO",
    0x56: "LAPRAS",
    0x57: "POLIWRATH",
    0x58: "MEOWTH",
    0x59: "CUBONE",
    0x5A: "PSYDUCK",
    0x5B: "NIDORAN ♂",
    0x5C: "NIDORINO",
    0x5D: "NIDORAN ♀",
    0x5E: "MACHOKE",
    0x5F: "PIDGEY",
    0x60: "PIDGEOT",
    0x61: "SPEAROW",
    0x62: "FEAROW",
    0x63: "SEEL",
    0x64: "KANGASKHAN",
    0x65: "SLOWPOKE",
    0x66: "DODUO",
    0x67: "VAPOREON",
    0x68: "POKE BALL",
    0x69: "FOSSIL",
    0x6A: "BOULDER",
    0x6B: "PAPER",
    0x6C: "POKEDEX",
    0x6D: "CLIPBOARD",
    0x6E: "SNORLAX",
    0x6F: "OLD AMBER",
    # 70 is unused.
    # 71 is unused.
    0x72: "GAMBLER ASLEEP",
    0x73: "JOLTEON",
    0x74: "FLAREON",
    0x75: "WIGGLYTUFF",
}
