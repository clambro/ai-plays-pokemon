import numpy as np
from pydantic import BaseModel

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y
from common.enums import AsciiTiles
from emulator.enums import MapLocation
from emulator.game_state import YellowLegacyGameState
from emulator.schemas import MapConnections, Sign, Sprite, Warp
from overworld_map.prompts import OVERWORLD_MAP_STR_FORMAT


class OverworldSprite(Sprite):
    """A sprite on the overworld map, known to the player."""

    description: str | None

    @classmethod
    def from_sprite(cls, sprite: Sprite, description: str | None) -> "OverworldSprite":
        """Create an overworld sprite from a sprite and a description."""
        return cls(**sprite.model_dump(), description=description)

    def to_string(self, map_id: MapLocation) -> str:
        """Get a string representation of the sprite."""
        description = self.description or "No description added yet."
        out = f"sprite_{map_id.value}_{self.index} at ({self.y}, {self.x}): {description}"
        if self.moves_randomly:
            out += (
                " Warning: This sprite wanders randomly around the map. Your reactions are likely"
                " too slow to catch it. Sprites like this are usually not worth interacting with."
            )
        return out


class OverworldWarp(Warp):
    """A warp on the overworld map, known to the player."""

    description: str | None

    @classmethod
    def from_warp(cls, warp: Warp, description: str | None) -> "OverworldWarp":
        """Create an overworld warp from a warp and a description."""
        return cls(**warp.model_dump(), description=description)

    def to_string(self, map_id: MapLocation) -> str:
        """Get a string representation of the warp."""
        description = self.description or "No description added yet."
        return (
            f"warp_{map_id.value}_{self.index} at ({self.y}, {self.x}) leading to"
            f" {self.destination.name}: {description}"
        )


class OverworldSign(Sign):
    """A sign on the overworld map, known to the player."""

    description: str | None

    @classmethod
    def from_sign(cls, sign: Sign, description: str | None) -> "OverworldSign":
        """Create an overworld sign from a sign and a description."""
        return cls(**sign.model_dump(), description=description)

    def to_string(self, map_id: MapLocation) -> str:
        """Get a string representation of the sign."""
        description = self.description or "No description added yet."
        return f"sign_{map_id.value}_{self.index} at ({self.y}, {self.x}): {description}"


class OverworldMap(BaseModel):
    """A map of a particular region of the overworld."""

    id: MapLocation
    ascii_tiles: list[list[str]]
    known_sprites: dict[int, OverworldSprite]
    known_warps: dict[int, OverworldWarp]
    known_signs: dict[int, OverworldSign]
    connections: MapConnections

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

    async def to_string(self, game_state: YellowLegacyGameState) -> str:
        """Return a string representation of the map."""
        tiles = self.ascii_tiles_str
        explored_percentage = np.mean(self.ascii_tiles_ndarray != AsciiTiles.UNSEEN)
        screen = game_state.get_ascii_screen().ndarray
        tile_above = screen[PLAYER_OFFSET_Y - 1, PLAYER_OFFSET_X]
        tile_below = screen[PLAYER_OFFSET_Y + 1, PLAYER_OFFSET_X]
        tile_left = screen[PLAYER_OFFSET_Y, PLAYER_OFFSET_X - 1]
        tile_right = screen[PLAYER_OFFSET_Y, PLAYER_OFFSET_X + 1]
        return OVERWORLD_MAP_STR_FORMAT.format(
            map_name=self.id.name,
            ascii_map=tiles,
            height=self.height,
            width=self.width,
            known_sprites=await self._get_sprite_notes(),
            known_warps=await self._get_warp_notes(),
            known_signs=await self._get_sign_notes(),
            explored_percentage=f"{explored_percentage:.0%}",
            ascii_screen="\n".join("".join(row) for row in screen),
            tile_above=tile_above,
            tile_below=tile_below,
            tile_left=tile_left,
            tile_right=tile_right,
            screen_upper_left_y=game_state.screen.top,
            screen_upper_left_x=game_state.screen.left,
            screen_lower_right_y=game_state.screen.bottom,
            screen_lower_right_x=game_state.screen.right,
            connections=self.connections,
        )

    async def _get_sprite_notes(self) -> str:
        """Get the notes for the sprites on the map, sorted by index."""
        if not self.known_sprites:
            return "No sprites discovered."
        return "\n".join(f"- {v.to_string(self.id)}" for _, v in sorted(self.known_sprites.items()))

    async def _get_warp_notes(self) -> str:
        """Get the notes for the warps on the map, sorted by index."""
        if not self.known_warps:
            return "No warp tiles discovered."
        return "\n".join(f"- {v.to_string(self.id)}" for _, v in sorted(self.known_warps.items()))

    async def _get_sign_notes(self) -> str:
        """Get the notes for the signs on the map, sorted by index."""
        if not self.known_signs:
            return "No signs discovered."
        return "\n".join(f"- {v.to_string(self.id)}" for _, v in sorted(self.known_signs.items()))
