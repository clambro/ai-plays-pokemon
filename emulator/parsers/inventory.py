from pyboy import PyBoyMemoryView
from pydantic import BaseModel

from common.enums import PokeballItem


class InventoryItem(BaseModel):
    """An item in the player's inventory."""

    name: str
    quantity: int


class Inventory(BaseModel):
    """The items in the player's inventory."""

    items: list[InventoryItem]


def parse_inventory(mem: PyBoyMemoryView) -> Inventory:
    """Parse the inventory from the memory."""
    num_items = mem[0xD31C]
    base_address = 0xD31D
    items = []
    for i in range(0, 2 * num_items, 2):  # Each item is 2 bytes: item_id, quantity.
        item_id = _INT_TO_ITEM_MAP.get(mem[base_address + i])
        quantity = mem[base_address + i + 1]
        if item_id is not None and quantity > 0:
            items.append(InventoryItem(name=item_id, quantity=quantity))
    return Inventory(items=items)


_INT_TO_ITEM_MAP = {
    0x01: PokeballItem.MASTER_BALL,
    0x02: PokeballItem.ULTRA_BALL,
    0x03: PokeballItem.GREAT_BALL,
    0x04: PokeballItem.POKE_BALL,
    0x05: "TOWN MAP",
    0x06: "BICYCLE",
    0x07: "SURFBOARD",
    0x08: "SAFARI BALL",
    0x09: "POKEDEX",
    0x0A: "MOON STONE",
    0x0B: "ANTIDOTE",
    0x0C: "BURN HEAL",
    0x0D: "ICE HEAL",
    0x0E: "AWAKENING",
    0x0F: "PARLYZ HEAL",
    0x10: "FULL RESTORE",
    0x11: "MAX POTION",
    0x12: "HYPER POTION",
    0x13: "SUPER POTION",
    0x14: "POTION",
    # Skip values 0x15-0x1C that represent badges.
    0x1D: "ESCAPE ROPE",
    0x1E: "REPEL",
    0x1F: "OLD AMBER",
    0x20: "FIRE STONE",
    0x21: "THUNDER STONE",
    0x22: "WATER STONE",
    0x23: "HP UP",
    0x24: "PROTEIN",
    0x25: "IRON",
    0x26: "CARBOS",
    0x27: "CALCIUM",
    0x28: "RARE CANDY",
    0x29: "DOME FOSSIL",
    0x2A: "HELIX FOSSIL",
    0x2B: "SECRET KEY",
    # 0x2C is unused.
    0x2D: "BIKE VOUCHER",
    0x2E: "X ACCURACY",
    0x2F: "LEAF STONE",
    0x30: "CARD KEY",
    0x31: "NUGGET",
    # 0x32 is unused.
    0x33: "POKE DOLL",
    0x34: "FULL HEAL",
    0x35: "REVIVE",
    0x36: "MAX REVIVE",
    0x37: "GUARD SPEC",
    0x38: "SUPER REPEL",
    0x39: "MAX REPEL",
    0x3A: "DIRE HIT",
    0x3B: "COIN",
    0x3C: "FRESH WATER",
    0x3D: "SODA POP",
    0x3E: "LEMONADE",
    0x3F: "S S TICKET",
    0x40: "GOLD TEETH",
    0x41: "X ATTACK",
    0x42: "X DEFEND",
    0x43: "X SPEED",
    0x44: "X SPECIAL",
    0x45: "COIN CASE",
    0x46: "OAKS PARCEL",
    0x47: "ITEMFINDER",
    0x48: "SILPH SCOPE",
    0x49: "POKE FLUTE",
    0x4A: "LIFT KEY",
    0x4B: "EXP ALL",
    0x4C: "OLD ROD",
    0x4D: "GOOD ROD",
    0x4E: "SUPER ROD",
    0x4F: "PP UP",
    0x50: "ETHER",
    0x51: "MAX ETHER",
    0x52: "ELIXER",
    0x53: "MAX ELIXER",
    # Numbers jump because a bunch of irrelevant constants are defined here.
    0xC4: "HM01 CUT",
    0xC5: "HM02 FLY",
    0xC6: "HM03 SURF",
    0xC7: "HM04 STRENGTH",
    0xC8: "HM05 FLASH",
    0xC9: "TM01 MEGA PUNCH",
    0xCA: "TM02 RAZOR WIND",
    0xCB: "TM03 SWORDS DANCE",
    0xCC: "TM04 FLAMETHROWER",
    0xCD: "TM05 MEGA KICK",
    0xCE: "TM06 TOXIC",
    0xCF: "TM07 HORN DRILL",
    0xD0: "TM08 BODY SLAM",
    0xD1: "TM09 TAKE DOWN",
    0xD2: "TM10 DOUBLE EDGE",
    0xD3: "TM11 BUBBLEBEAM",
    0xD4: "TM12 WATER GUN",
    0xD5: "TM13 ICE BEAM",
    0xD6: "TM14 BLIZZARD",
    0xD7: "TM15 HYPER BEAM",
    0xD8: "TM16 PAY DAY",
    0xD9: "TM17 SUBMISSION",
    0xDA: "TM18 COUNTER",
    0xDB: "TM19 SEISMIC TOSS",
    0xDC: "TM20 RAGE",
    0xDD: "TM21 MEGA DRAIN",
    0xDE: "TM22 SOLARBEAM",
    0xDF: "TM23 DRAGON RAGE",
    0xE0: "TM24 THUNDERBOLT",
    0xE1: "TM25 THUNDER",
    0xE2: "TM26 EARTHQUAKE",
    0xE3: "TM27 FISSURE",
    0xE4: "TM28 DIG",
    0xE5: "TM29 PSYCHIC M",
    0xE6: "TM30 TELEPORT",
    0xE7: "TM31 MIMIC",
    0xE8: "TM32 DOUBLE TEAM",
    0xE9: "TM33 REFLECT",
    0xEA: "TM34 BIDE",
    0xEB: "TM35 METRONOME",
    0xEC: "TM36 SELFDESTRUCT",
    0xED: "TM37 EGG BOMB",
    0xEE: "TM38 FIRE BLAST",
    0xEF: "TM39 SWIFT",
    0xF0: "TM40 SKULL BASH",
    0xF1: "TM41 SOFTBOILED",
    0xF2: "TM42 DREAM EATER",
    0xF3: "TM43 SKY ATTACK",
    0xF4: "TM44 REST",
    0xF5: "TM45 THUNDER WAVE",
    0xF6: "TM46 PSYWAVE",
    0xF7: "TM47 EXPLOSION",
    0xF8: "TM48 ROCK SLIDE",
    0xF9: "TM49 TRI ATTACK",
    0xFA: "TM50 SUBSTITUTE",
}
