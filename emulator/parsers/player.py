from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.enums import Badge, FacingDirection
from common.schemas import Coords
from emulator.parsers.utils import get_text_from_byte_array


class Player(BaseModel):
    """The state of the player character."""

    name: str
    coords: Coords
    direction: FacingDirection
    money: int
    badges: list[Badge]
    level_cap: int
    pokedex_caught: int
    pokedex_seen: int
    play_time_seconds: int

    model_config = ConfigDict(frozen=True)


def parse_player(mem: PyBoyMemoryView) -> Player:
    """
    Create a new player state from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the player state from.
    :return: A new player state.
    """
    name = get_text_from_byte_array(mem[0xD157 : 0xD157 + 0xB])
    if name == "NINTEN":
        name = ""  # This is a hack. It's the default name in memory before you choose a name.

    badges = _read_badges(mem)

    play_time_hours = mem[0xDA40]
    play_time_minutes = mem[0xDA42]
    play_time_seconds = mem[0xDA43]
    play_time_seconds += (play_time_hours * 3600) + (play_time_minutes * 60)

    # Pokemon seen and caught are represented as one bit each in the following bytes.
    pokedex_caught = sum(mem[i].bit_count() for i in range(0xD2F6, 0xD309))
    pokedex_seen = sum(mem[i].bit_count() for i in range(0xD309, 0xD31C))

    return Player(
        name=name,
        coords=Coords(row=mem[0xD3AE], col=mem[0xD3AF]),
        direction=_INT_TO_FACING_DIRECTION[mem[0xD577]],
        money=_read_money(mem),
        badges=badges,
        level_cap=_read_level_cap(mem, len(badges)),
        pokedex_caught=pokedex_caught,
        pokedex_seen=pokedex_seen,
        play_time_seconds=play_time_seconds,
    )


def _read_money(mem: PyBoyMemoryView) -> int:
    """
    Read the player's money from the binary coded decimal format.

    :param mem: The PyBoyMemoryView instance to read the money from.
    :return: The player's money.
    """
    m1 = mem[0xD394]
    m2 = mem[0xD395]
    m3 = mem[0xD396]
    return (
        ((m1 >> 4) * 100000)
        + ((m1 & 0xF) * 10000)
        + ((m2 >> 4) * 1000)
        + ((m2 & 0xF) * 100)
        + ((m3 >> 4) * 10)
        + (m3 & 0xF)
    )


def _read_badges(mem: PyBoyMemoryView) -> list[Badge]:
    """Read the player's badges from the memory."""
    badge_byte = mem[0xD3A3]
    badges = []
    for badge_id, badge_name in _INT_TO_BADGE.items():
        if badge_byte & badge_id:
            badges.append(badge_name)
    return badges


def _read_level_cap(mem: PyBoyMemoryView, num_badges: int) -> int:
    """Read the player's level cap from the memory."""
    champion_byte = mem[0xD745]
    if champion_byte:
        return 100
    return _INT_TO_LEVEL_CAP[num_badges]


_INT_TO_FACING_DIRECTION = {
    0: FacingDirection.UP,  # Zero is the default value at the start of the game.
    1: FacingDirection.RIGHT,
    2: FacingDirection.LEFT,
    4: FacingDirection.DOWN,
    8: FacingDirection.UP,
}
_INT_TO_BADGE = {
    1 << 0: Badge.BOULDERBADGE,
    1 << 1: Badge.CASCADEBADGE,
    1 << 2: Badge.THUNDERBADGE,
    1 << 3: Badge.RAINBOWBADGE,
    1 << 4: Badge.SOULBADGE,
    1 << 5: Badge.MARSHBADGE,
    1 << 6: Badge.VOLCANOBADGE,
    1 << 7: Badge.EARTHBADGE,
}
_INT_TO_LEVEL_CAP = {
    0: 12,
    1: 21,
    2: 24,
    3: 35,
    4: 43,
    5: 50,
    6: 53,
    7: 55,
    8: 65,
}
