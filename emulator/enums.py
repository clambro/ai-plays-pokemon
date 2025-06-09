from enum import IntEnum, StrEnum


class Button(StrEnum):
    """The buttons that can be pressed in the game."""

    A = "a"
    B = "b"
    START = "start"
    SELECT = "select"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class FacingDirection(IntEnum):
    """The direction the player is facing."""

    NONE = 0
    UP = 8
    DOWN = 4
    LEFT = 2
    RIGHT = 1


class BadgeId(IntEnum):
    """Enum of badges."""

    BOULDERBADGE = 1 << 0
    CASCADEBADGE = 1 << 1
    THUNDERBADGE = 1 << 2
    RAINBOWBADGE = 1 << 3
    SOULBADGE = 1 << 4
    MARSHBADGE = 1 << 5
    VOLCANOBADGE = 1 << 6
    EARTHBADGE = 1 << 7

    @classmethod
    def from_badge_byte(cls, badge_byte: int) -> list["BadgeId"]:
        """Convert a byte to a list of badge IDs."""
        return [badge for badge in cls if badge_byte & badge.value]

    @classmethod
    def get_level_cap(cls, badge_byte: int, champion_byte: int) -> int:
        """Get the current level cap for the player's team based on the number of badges."""
        if champion_byte:
            return 100
        num_badges = sum(1 for badge in cls if badge_byte & badge.value)
        level_cap_map = {
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
        return level_cap_map[num_badges]
