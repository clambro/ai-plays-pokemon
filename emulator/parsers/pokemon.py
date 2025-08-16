import math

from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from emulator.parsers.utils import get_text_from_byte_array


class PokemonMove(BaseModel):
    """A move that a pokemon can learn."""

    name: str
    pp: int

    model_config = ConfigDict(frozen=True)


class Pokemon(BaseModel):
    """The state of a player's pokemon."""

    name: str
    species: str
    type1: str
    type2: str | None
    level: int
    hp: int
    max_hp: int
    status: str | None
    moves: list[PokemonMove]

    model_config = ConfigDict(frozen=True)


class EnemyPokemon(BaseModel):
    """The state of an enemy pokemon in the battle."""

    species: str
    level: int
    hp_pct: float
    status: str | None


def parse_party_pokemon(mem: PyBoyMemoryView) -> list[Pokemon]:
    """Parse the player's pokemon from the memory."""
    party = []
    for i in range(mem[0xD162]):
        pokemon = _parse_party_pokemon(mem, i)
        if pokemon is not None:
            party.append(pokemon)
    return party


def parse_pc_pokemon(mem: PyBoyMemoryView) -> list[Pokemon]:
    """Parse the PC's pokemon from the memory."""
    pc = []
    for i in range(mem[0xDA7F]):
        pokemon = _parse_pc_pokemon(mem, i)
        if pokemon is not None:
            pc.append(pokemon)
    return pc


def parse_player_battle_pokemon(mem: PyBoyMemoryView) -> Pokemon | None:
    """Parse a single player pokemon from the memory."""
    species_id = mem[0xD013]
    if species_id == 0:
        return None

    name = get_text_from_byte_array(mem[0xD008:0xD013])

    type1 = _INT_TO_TYPE_MAP[mem[0xD018]]
    type2 = _INT_TO_TYPE_MAP[mem[0xD019]]
    type2 = type2 if type1 != type2 else None  # Monotype pokemon have the same type for both.

    moves = []
    for i in range(4):
        move_id = mem[0xD01B + i]
        if move_id == 0:
            continue
        pp = mem[0xD02C + i]
        moves.append(PokemonMove(name=_INT_TO_MOVE_MAP[move_id], pp=pp))

    hp = (mem[0xD014] << 8) | mem[0xD015]
    max_hp = (mem[0xD022] << 8) | mem[0xD023]

    status_loc = mem[0xD022]
    status = _INT_TO_STATUS_MAP[status_loc] if status_loc != 0 else None

    return Pokemon(
        name=name,
        species=_INT_TO_SPECIES_MAP[species_id],
        type1=type1,
        type2=type2,
        level=mem[0xD021],
        hp=hp,
        max_hp=max_hp,
        status=status,
        moves=moves,
    )


def parse_enemy_battle_pokemon(mem: PyBoyMemoryView) -> EnemyPokemon | None:
    """Parse the enemy's pokemon from the memory."""
    species_id = mem[0xCFE4]
    if species_id == 0:
        return None

    hp = (mem[0xCFE5] << 8) | mem[0xCFE6]
    max_hp = (mem[0xCFF3] << 8) | mem[0xCFF4]

    # The gen 1 health bar is 48 pixels long, so about 2% resolution for health percentage.
    hp_pct = math.ceil(hp / max_hp * 50) * 2

    status_loc = mem[0xCFF3]
    status = _INT_TO_STATUS_MAP[status_loc] if status_loc != 0 else None

    return EnemyPokemon(
        species=_INT_TO_SPECIES_MAP[species_id],
        level=mem[0xCFF2],
        hp_pct=hp_pct,
        status=status,
    )


def _parse_party_pokemon(mem: PyBoyMemoryView, index: int) -> Pokemon | None:
    """Parse a single player pokemon from the memory."""
    increment = index * 0x2C
    species_id = mem[0xD16A + increment]
    if species_id == 0:
        return None

    name = get_text_from_byte_array(mem[0xD2B4 + 0xB * index : 0xD2B4 + 0xB * (index + 1)])

    type1 = _INT_TO_TYPE_MAP[mem[0xD16F + increment]]
    type2 = _INT_TO_TYPE_MAP[mem[0xD170 + increment]]
    type2 = type2 if type1 != type2 else None  # Monotype pokemon have the same type for both.

    moves = []
    for i in range(4):
        move_id = mem[0xD172 + increment + i]
        if move_id == 0:
            continue
        pp = mem[0xD187 + increment + i]
        moves.append(PokemonMove(name=_INT_TO_MOVE_MAP[move_id], pp=pp))

    hp = (mem[0xD16B + increment] << 8) | mem[0xD16B + increment + 1]
    max_hp = (mem[0xD18C + increment] << 8) | mem[0xD18C + increment + 1]

    status_loc = mem[0xD16E + increment]
    status = _INT_TO_STATUS_MAP[status_loc] if status_loc != 0 else None

    return Pokemon(
        name=name,
        species=_INT_TO_SPECIES_MAP[species_id],
        type1=type1,
        type2=type2,
        level=mem[0xD18B + increment],
        hp=hp,
        max_hp=max_hp,
        status=status,
        moves=moves,
    )


def _parse_pc_pokemon(mem: PyBoyMemoryView, index: int) -> Pokemon | None:
    """Parse a single PC pokemon from the memory."""
    increment = index * 0x21
    species_id = mem[0xDA95 + increment]
    if species_id == 0:
        return None

    name = get_text_from_byte_array(mem[0xDE05 + 0xB * index : 0xDE05 + 0xB * (index + 1)])

    type1 = _INT_TO_TYPE_MAP[mem[0xDA9A + increment]]
    type2 = _INT_TO_TYPE_MAP[mem[0xDA9B + increment]]
    type2 = type2 if type1 != type2 else None  # Monotype pokemon have the same type for both.

    moves = []
    for i in range(4):
        move_id = mem[0xDA9D + increment + i]
        if move_id == 0:
            continue
        pp = mem[0xDAB2 + increment + i]
        moves.append(PokemonMove(name=_INT_TO_MOVE_MAP[move_id], pp=pp))

    max_hp = (mem[0xDA96 + increment] << 8) | mem[0xDA96 + increment + 1]

    return Pokemon(
        name=name,
        species=_INT_TO_SPECIES_MAP[species_id],
        type1=type1,
        type2=type2,
        level=mem[0xDA98 + increment],
        hp=max_hp,  # Always at max HP when in the PC.
        max_hp=max_hp,
        status=None,  # No status ailments when in the PC.
        moves=moves,
    )


_INT_TO_SPECIES_MAP = {
    0x01: "RHYDON",
    0x02: "KANGASKHAN",
    0x03: "NIDORAN ♂",
    0x04: "CLEFAIRY",
    0x05: "SPEAROW",
    0x06: "VOLTORB",
    0x07: "NIDOKING",
    0x08: "SLOWBRO",
    0x09: "IVYSAUR",
    0x0A: "EXEGGUTOR",
    0x0B: "LICKITUNG",
    0x0C: "EXEGGCUTE",
    0x0D: "GRIMER",
    0x0E: "GENGAR",
    0x0F: "NIDORAN ♀",
    0x10: "NIDOQUEEN",
    0x11: "CUBONE",
    0x12: "RHYHORN",
    0x13: "LAPRAS",
    0x14: "ARCANINE",
    0x15: "MEW",
    0x16: "GYARADOS",
    0x17: "SHELLDER",
    0x18: "TENTACOOL",
    0x19: "GASTLY",
    0x1A: "SCYTHER",
    0x1B: "STARYU",
    0x1C: "BLASTOISE",
    0x1D: "PINSIR",
    0x1E: "TANGELA",
    0x21: "GROWLITHE",
    0x22: "ONIX",
    0x23: "FEAROW",
    0x24: "PIDGEY",
    0x25: "SLOWPOKE",
    0x26: "KADABRA",
    0x27: "GRAVELER",
    0x28: "CHANSEY",
    0x29: "MACHOKE",
    0x2A: "MR MIME",
    0x2B: "HITMONLEE",
    0x2C: "HITMONCHAN",
    0x2D: "ARBOK",
    0x2E: "PARASECT",
    0x2F: "PSYDUCK",
    0x30: "DROWZEE",
    0x31: "GOLEM",
    0x33: "MAGMAR",
    0x35: "ELECTABUZZ",
    0x36: "MAGNETON",
    0x37: "KOFFING",
    0x39: "MANKEY",
    0x3A: "SEEL",
    0x3B: "DIGLETT",
    0x3C: "TAUROS",
    0x40: "FARFETCHD",
    0x41: "VENONAT",
    0x42: "DRAGONITE",
    0x46: "DODUO",
    0x47: "POLIWAG",
    0x48: "JYNX",
    0x49: "MOLTRES",
    0x4A: "ARTICUNO",
    0x4B: "ZAPDOS",
    0x4C: "DITTO",
    0x4D: "MEOWTH",
    0x4E: "KRABBY",
    0x52: "VULPIX",
    0x53: "NINETALES",
    0x54: "PIKACHU",
    0x55: "RAICHU",
    0x58: "DRATINI",
    0x59: "DRAGONAIR",
    0x5A: "KABUTO",
    0x5B: "KABUTOPS",
    0x5C: "HORSEA",
    0x5D: "SEADRA",
    0x60: "SANDSHREW",
    0x61: "SANDSLASH",
    0x62: "OMANYTE",
    0x63: "OMASTAR",
    0x64: "JIGGLYPUFF",
    0x65: "WIGGLYTUFF",
    0x66: "EEVEE",
    0x67: "FLAREON",
    0x68: "JOLTEON",
    0x69: "VAPOREON",
    0x6A: "MACHOP",
    0x6B: "ZUBAT",
    0x6C: "EKANS",
    0x6D: "PARAS",
    0x6E: "POLIWHIRL",
    0x6F: "POLIWRATH",
    0x70: "WEEDLE",
    0x71: "KAKUNA",
    0x72: "BEEDRILL",
    0x74: "DODRIO",
    0x75: "PRIMEAPE",
    0x76: "DUGTRIO",
    0x77: "VENOMOTH",
    0x78: "DEWGONG",
    0x7B: "CATERPIE",
    0x7C: "METAPOD",
    0x7D: "BUTTERFREE",
    0x7E: "MACHAMP",
    0x80: "GOLDUCK",
    0x81: "HYPNO",
    0x82: "GOLBAT",
    0x83: "MEWTWO",
    0x84: "SNORLAX",
    0x85: "MAGIKARP",
    0x8B: "CLOYSTER",
    0x88: "MUK",
    0x8A: "KINGLER",
    0x8D: "ELECTRODE",
    0x8E: "CLEFABLE",
    0x8F: "WEEZING",
    0x90: "PERSIAN",
    0x91: "MAROWAK",
    0x93: "HAUNTER",
    0x94: "ABRA",
    0x95: "ALAKAZAM",
    0x96: "PIDGEOTTO",
    0x97: "PIDGEOT",
    0x98: "STARMIE",
    0x99: "BULBASAUR",
    0x9A: "VENUSAUR",
    0x9B: "TENTACRUEL",
    0x9D: "GOLDEEN",
    0x9E: "SEAKING",
    0xA3: "PONYTA",
    0xA4: "RAPIDASH",
    0xA5: "RATTATA",
    0xA6: "RATICATE",
    0xA7: "NIDORINO",
    0xA8: "NIDORINA",
    0xA9: "GEODUDE",
    0xAA: "PORYGON",
    0xAB: "AERODACTYL",
    0xAD: "MAGNEMITE",
    0xB0: "CHARMANDER",
    0xB1: "SQUIRTLE",
    0xB2: "CHARMELEON",
    0xB3: "WARTORTLE",
    0xB4: "CHARIZARD",
    0xB8: "GHOST",  # This is the ghost in the Pokemon Tower.
    0xB9: "ODDISH",
    0xBA: "GLOOM",
    0xBB: "VILEPLUME",
    0xBC: "BELLSPROUT",
    0xBD: "WEEPINBELL",
    0xBE: "VICTREEBEL",
}
_INT_TO_TYPE_MAP = {
    0x00: "NORMAL",
    0x01: "FIGHTING",
    0x02: "FLYING",
    0x03: "POISON",
    0x04: "GROUND",
    0x05: "ROCK",
    0x06: "BIRD",
    0x07: "BUG",
    0x08: "GHOST",
    0x14: "FIRE",
    0x15: "WATER",
    0x16: "GRASS",
    0x17: "ELECTRIC",
    0x18: "PSYCHIC",
    0x19: "ICE",
    0x1A: "DRAGON",
}
_ASLEEP = "ASLEEP"
_INT_TO_STATUS_MAP = {
    0b1: _ASLEEP,  # One for each turn of sleep, but we aren't supposed to know how many turns.
    0b10: _ASLEEP,
    0b11: _ASLEEP,
    0b100: _ASLEEP,
    0b101: _ASLEEP,
    0b110: _ASLEEP,
    0b111: _ASLEEP,
    1 << 3: "POISONED",
    1 << 4: "BURNED",
    1 << 5: "FROZEN",
    1 << 6: "PARALYZED",
}
_INT_TO_MOVE_MAP = {
    0x01: "POUND",
    0x02: "KARATE CHOP",
    0x03: "DOUBLESLAP",
    0x04: "COMET PUNCH",
    0x05: "MEGA PUNCH",
    0x06: "PAY DAY",
    0x07: "FIRE PUNCH",
    0x08: "ICE PUNCH",
    0x09: "THUNDERPUNCH",
    0x0A: "SCRATCH",
    0x0B: "VICEGRIP",
    0x0C: "GUILLOTINE",
    0x0D: "RAZOR WIND",
    0x0E: "SWORDS DANCE",
    0x0F: "CUT",
    0x10: "GUST",
    0x11: "WING ATTACK",
    0x12: "WHIRLWIND",
    0x13: "FLY",
    0x14: "BIND",
    0x15: "SLAM",
    0x16: "VINE WHIP",
    0x17: "STOMP",
    0x18: "DOUBLE KICK",
    0x19: "MEGA KICK",
    0x1A: "JUMP KICK",
    0x1B: "ROLLING KICK",
    0x1C: "SAND ATTACK",
    0x1D: "HEADBUTT",
    0x1E: "HORN ATTACK",
    0x1F: "FURY ATTACK",
    0x20: "HORN DRILL",
    0x21: "TACKLE",
    0x22: "BODY SLAM",
    0x23: "WRAP",
    0x24: "TAKE DOWN",
    0x25: "THRASH",
    0x26: "DOUBLE EDGE",
    0x27: "TAIL WHIP",
    0x28: "POISON STING",
    0x29: "TWINEEDLE",
    0x2A: "PIN MISSILE",
    0x2B: "LEER",
    0x2C: "BITE",
    0x2D: "GROWL",
    0x2E: "ROAR",
    0x2F: "SING",
    0x30: "SUPERSONIC",
    0x31: "SONICBOOM",
    0x32: "DISABLE",
    0x33: "ACID",
    0x34: "EMBER",
    0x35: "FLAMETHROWER",
    0x36: "MIST",
    0x37: "WATER GUN",
    0x38: "HYDRO PUMP",
    0x39: "SURF",
    0x3A: "ICE BEAM",
    0x3B: "BLIZZARD",
    0x3C: "PSYBEAM",
    0x3D: "BUBBLEBEAM",
    0x3E: "AURORA BEAM",
    0x3F: "HYPER BEAM",
    0x40: "PECK",
    0x41: "DRILL PECK",
    0x42: "SUBMISSION",
    0x43: "LOW KICK",
    0x44: "COUNTER",
    0x45: "SEISMIC TOSS",
    0x46: "STRENGTH",
    0x47: "ABSORB",
    0x48: "MEGA DRAIN",
    0x49: "LEECH SEED",
    0x4A: "GROWTH",
    0x4B: "RAZOR LEAF",
    0x4C: "SOLARBEAM",
    0x4D: "POISONPOWDER",
    0x4E: "STUN SPORE",
    0x4F: "SLEEP POWDER",
    0x50: "PETAL DANCE",
    0x51: "STRING SHOT",
    0x52: "DRAGON RAGE",
    0x53: "FIRE SPIN",
    0x54: "THUNDERSHOCK",
    0x55: "THUNDERBOLT",
    0x56: "THUNDER WAVE",
    0x57: "THUNDER",
    0x58: "ROCK THROW",
    0x59: "EARTHQUAKE",
    0x5A: "FISSURE",
    0x5B: "DIG",
    0x5C: "TOXIC",
    0x5D: "CONFUSION",
    0x5E: "PSYCHIC",
    0x5F: "HYPNOSIS",
    0x60: "MEDITATE",
    0x61: "AGILITY",
    0x62: "QUICK ATTACK",
    0x63: "RAGE",
    0x64: "TELEPORT",
    0x65: "NIGHT SHADE",
    0x66: "MIMIC",
    0x67: "SCREECH",
    0x68: "DOUBLE TEAM",
    0x69: "RECOVER",
    0x6A: "HARDEN",
    0x6B: "MINIMIZE",
    0x6C: "SMOKESCREEN",
    0x6D: "CONFUSE RAY",
    0x6E: "WITHDRAW",
    0x6F: "DEFENSE CURL",
    0x70: "BARRIER",
    0x71: "LIGHT SCREEN",
    0x72: "HAZE",
    0x73: "REFLECT",
    0x74: "FOCUS ENERGY",
    0x75: "BIDE",
    0x76: "METRONOME",
    0x77: "MIRROR MOVE",
    0x78: "SELFDESTRUCT",
    0x79: "EGG BOMB",
    0x7A: "LICK",
    0x7B: "SMOG",
    0x7C: "SLUDGE",
    0x7D: "BONE CLUB",
    0x7E: "FIRE BLAST",
    0x7F: "WATERFALL",
    0x80: "CLAMP",
    0x81: "SWIFT",
    0x82: "SKULL BASH",
    0x83: "SPIKE CANNON",
    0x84: "CONSTRICT",
    0x85: "AMNESIA",
    0x86: "KINESIS",
    0x87: "SOFTBOILED",
    0x88: "HI JUMP KICK",
    0x89: "GLARE",
    0x8A: "DREAM EATER",
    0x8B: "POISON GAS",
    0x8C: "BARRAGE",
    0x8D: "LEECH LIFE",
    0x8E: "LOVELY KISS",
    0x8F: "SKY ATTACK",
    0x90: "TRANSFORM",
    0x91: "BUBBLE",
    0x92: "DIZZY PUNCH",
    0x93: "SPORE",
    0x94: "FLASH",
    0x95: "PSYWAVE",
    0x96: "SPLASH",
    0x97: "ACID ARMOR",
    0x98: "CRABHAMMER",
    0x99: "EXPLOSION",
    0x9A: "FURY SWIPES",
    0x9B: "BONEMERANG",
    0x9C: "REST",
    0x9D: "ROCK SLIDE",
    0x9E: "HYPER FANG",
    0x9F: "SHARPEN",
    0xA0: "CONVERSION",
    0xA1: "TRI ATTACK",
    0xA2: "SUPER FANG",
    0xA3: "SLASH",
    0xA4: "SUBSTITUTE",
    0xA5: "STRUGGLE",
}
