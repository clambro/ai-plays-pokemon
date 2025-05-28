from enum import StrEnum


class AgentStateHandler(StrEnum):
    """An enum for the different state handlers."""

    OVERWORLD = "overworld"
    BATTLE = "battle"
    TEXT = "text"


class Tool(StrEnum):
    """An enum for the different tools."""

    NAVIGATION = "navigation"


class AsciiTiles(StrEnum):
    """An enum for the ASCII representations of overworld map tiles."""

    UNSEEN = "?"
    WALL = "x"
    WATER = "~"
    GRASS = "*"
    LEDGE = "-"
    FREE = "."
    PLAYER = "P"
    SPRITE = "S"
    WARP = "W"
    CUT_TREE = "T"
    PIKACHU = "k"
    SIGN = "!"

    @classmethod
    def get_walkable_tiles(cls) -> list["AsciiTiles"]:
        """Get the walkable tiles."""
        return [cls.FREE, cls.GRASS, cls.WARP, cls.PIKACHU]


class MapEntityType(StrEnum):
    """An enum for the different types of map entities."""

    WARP = "warp"
    SPRITE = "sprite"
    SIGN = "sign"
