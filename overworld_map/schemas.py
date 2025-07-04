import numpy as np
from pydantic import BaseModel

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y
from common.enums import AsciiTile, BlockedDirection, MapId, WarpType
from common.schemas import Coords
from emulator.game_state import YellowLegacyGameState
from emulator.schemas import Sign, Sprite, Warp
from overworld_map.prompts import OVERWORLD_MAP_STR_FORMAT

DEFAULT_ENTITY_DESCRIPTION = (
    "No description added yet. Approach and interact with this entity to add a description."
)


class OverworldSprite(Sprite):
    """A sprite on the overworld map, known to the player."""

    description: str | None

    @classmethod
    def from_sprite(cls, sprite: Sprite, description: str | None) -> "OverworldSprite":
        """Create an overworld sprite from a sprite and a description."""
        return cls(**sprite.model_dump(), description=description)

    def to_string(self, map_id: MapId) -> str:
        """Get a string representation of the sprite."""
        description = self.description or DEFAULT_ENTITY_DESCRIPTION
        out = f"sprite_{map_id}_{self.index} at {self.coords}: {description}"
        if self.moves_randomly:
            out += (
                " Warning: This sprite wanders randomly around the map. Your reactions are too slow"
                " to catch it. Sprites like this are not worth interacting with."
            )
        return out


class OverworldSign(Sign):
    """A sign on the overworld map, known to the player."""

    description: str | None

    @classmethod
    def from_sign(cls, sign: Sign, description: str | None) -> "OverworldSign":
        """Create an overworld sign from a sign and a description."""
        return cls(**sign.model_dump(), description=description)

    def to_string(self, map_id: MapId) -> str:
        """Get a string representation of the sign."""
        description = self.description or DEFAULT_ENTITY_DESCRIPTION
        return f"sign_{map_id}_{self.index} at {self.coords}: {description}"


class OverworldWarp(Warp):
    """
    A warp on the overworld map, known to the player.

    Unlike signs and sprites, warps are static. The description is immutable.
    """

    visited: bool

    @property
    def description(self) -> str:
        """Get a description of the warp."""
        if self.warp_type == WarpType.SINGLE:
            return "This is a single warp tile. Stand on it to warp."
        if self.warp_type == WarpType.DOUBLE_VERTICAL and self.coords.col == 0:
            return (
                "This is a vertical double warp tile. Stand on either tile and walk LEFT to warp."
            )
        if self.warp_type == WarpType.DOUBLE_VERTICAL:
            return (
                "This is a vertical double warp tile. Stand on either tile and walk RIGHT to warp."
            )
        if self.warp_type == WarpType.DOUBLE_HORIZONTAL and self.coords.row == 0:
            return (
                "This is a horizontal double warp tile. Stand on either tile and walk UP to warp."
            )
        if self.warp_type == WarpType.DOUBLE_HORIZONTAL:
            return (
                "This is a horizontal double warp tile. Stand on either tile and walk DOWN to warp."
            )
        raise ValueError(f"Unknown warp type: {self.warp_type}")

    @classmethod
    def from_warp(cls, warp: Warp, visited_maps: list[MapId]) -> "OverworldWarp":
        """Create an overworld warp from a warp."""
        # The OUTSIDE placeholder map is not in the DB, so we assume it's always visited.
        visited = warp.destination in visited_maps or warp.destination == MapId.OUTSIDE
        return cls(**warp.model_dump(), visited=visited)

    def to_string(self, map_id: MapId) -> str:
        """Get a string representation of the warp."""
        visited_text = "" if self.visited else "You have not been to this map yet. "
        return (
            f"warp_{map_id}_{self.index} at {self.coords} leading to {self.destination.name}."
            f" {visited_text}{self.description}"
        )


class OverworldMap(BaseModel):
    """A map of a particular region of the overworld."""

    id: MapId
    ascii_tiles: list[list[str]]
    blockages: dict[Coords, BlockedDirection]
    known_sprites: dict[int, OverworldSprite]
    known_signs: dict[int, OverworldSign]
    known_warps: dict[int, OverworldWarp]
    north_connection: MapId | None
    south_connection: MapId | None
    east_connection: MapId | None
    west_connection: MapId | None

    @property
    def height(self) -> int:
        """The height of the map."""
        return len(self.ascii_tiles)

    @property
    def width(self) -> int:
        """The width of the map."""
        return len(self.ascii_tiles[0])

    @property
    def ascii_tiles_ndarray(self) -> np.ndarray:
        """The ascii tiles as a numpy array."""
        return np.array(self.ascii_tiles)

    @property
    def ascii_tiles_str(self) -> str:
        """The ascii tiles as a string."""
        return "\n".join("".join(row) for row in self.ascii_tiles)

    def to_string(self, game_state: YellowLegacyGameState) -> str:
        """Return a string representation of the map."""
        tiles = self.ascii_tiles_str
        explored_percentage = np.mean(self.ascii_tiles_ndarray != AsciiTile.UNSEEN)
        tile_above, blocked_above = self._get_tile_notes(BlockedDirection.UP)
        tile_below, blocked_below = self._get_tile_notes(BlockedDirection.DOWN)
        tile_left, blocked_left = self._get_tile_notes(BlockedDirection.LEFT)
        tile_right, blocked_right = self._get_tile_notes(BlockedDirection.RIGHT)
        return OVERWORLD_MAP_STR_FORMAT.format(
            map_name=self.id.name,
            ascii_map=tiles,
            height=self.height,
            width=self.width,
            known_sprites=self._get_sprite_notes(),
            known_warps=self._get_warp_notes(),
            known_signs=self._get_sign_notes(),
            explored_percentage=f"{explored_percentage:.0%}",
            ascii_screen=game_state.get_ascii_screen(),
            player_coords=game_state.player.coords,
            player_direction=game_state.player.direction,
            tile_above=tile_above,
            blocked_above=blocked_above,
            tile_below=tile_below,
            blocked_below=blocked_below,
            tile_left=tile_left,
            blocked_left=blocked_left,
            tile_right=tile_right,
            blocked_right=blocked_right,
            screen_top=game_state.screen.top,
            screen_left=game_state.screen.left,
            screen_bottom=game_state.screen.bottom,
            screen_right=game_state.screen.right,
            connections=self._get_connection_notes(),
        )

    def _get_tile_notes(self, direction: BlockedDirection) -> tuple[str, str]:
        """
        Get the adjacent tile and blocking notes for the player's current position in the given
        direction.

        :param blocked: The blocked direction.
        :return: A tuple of the adjacent tile and blocking notes.
        """
        text = ", but your movement in this direction is blocked by an elevation difference."
        row_col_map = {
            BlockedDirection.UP: (PLAYER_OFFSET_Y - 1, PLAYER_OFFSET_X),
            BlockedDirection.DOWN: (PLAYER_OFFSET_Y + 1, PLAYER_OFFSET_X),
            BlockedDirection.LEFT: (PLAYER_OFFSET_Y, PLAYER_OFFSET_X - 1),
            BlockedDirection.RIGHT: (PLAYER_OFFSET_Y, PLAYER_OFFSET_X + 1),
        }
        row, col = row_col_map[direction]

        tile = self.ascii_tiles_ndarray[row, col]
        blockage = self.blockages.get(Coords(row=row, col=col))
        blocked_text = text if blockage and blockage & direction else ""
        return tile, blocked_text

    def _get_sprite_notes(self) -> str:
        """Get the notes for the sprites on the map, sorted by index."""
        if not self.known_sprites:
            return "No sprites discovered."
        return "\n".join(f"- {v.to_string(self.id)}" for _, v in sorted(self.known_sprites.items()))

    def _get_warp_notes(self) -> str:
        """Get the notes for the warps on the map, sorted by index."""
        if not self.known_warps:
            return "No warp tiles discovered."
        return "\n".join(f"- {v.to_string(self.id)}" for _, v in sorted(self.known_warps.items()))

    def _get_sign_notes(self) -> str:
        """Get the notes for the signs on the map, sorted by index."""
        if not self.known_signs:
            return "No signs discovered."
        return "\n".join(f"- {v.to_string(self.id)}" for _, v in sorted(self.known_signs.items()))

    def _get_connection_notes(self) -> str:
        """Get a string representation of the map connections."""
        if (
            not self.north_connection
            and not self.south_connection
            and not self.east_connection
            and not self.west_connection
        ):
            return (
                "There are no direct connections to other maps on this map. The only way to leave"
                " this map is via warp tiles."
            )
        out = ""
        for direction, connection in [
            ("north", self.north_connection),
            ("south", self.south_connection),
            ("east", self.east_connection),
            ("west", self.west_connection),
        ]:
            if connection is not None:
                out += f"The map to the {direction} is {connection.name}.\n"
            else:
                out += f"There is no map connection to the {direction}.\n"
        return out.strip()
