from pathlib import Path
import aiofiles
import numpy as np
from pydantic import BaseModel

from common.constants import MAP_SUBFOLDER, UNSEEN_TILE
from emulator.enums import MapLocation
from emulator.schemas import ScreenState, Sprite, Warp
from emulator.game_state import YellowLegacyGameState
from overworld_map.prompts import OVERWORLD_MAP_STR_FORMAT


class OverworldMap(BaseModel):
    """A map of a particular region of the overworld."""

    id: MapLocation
    ascii_tiles: list[list[str]]
    known_sprites: dict[int, Sprite]
    known_warps: dict[int, Warp]

    @classmethod
    async def load(cls, parent_folder: Path, id: MapLocation) -> "OverworldMap":
        """Load a map from a file."""
        file_path = parent_folder / MAP_SUBFOLDER / f"{id.name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Map file not found: {file_path}")
        async with aiofiles.open(file_path) as f:
            data = await f.read()
        return cls.model_validate_json(data)

    @classmethod
    async def from_game_state(cls, game_state: YellowLegacyGameState) -> "OverworldMap":
        """Load a map from the game state."""
        tiles = []
        for _ in range(game_state.cur_map.height):
            row = []
            for _ in range(game_state.cur_map.width):
                row.append(UNSEEN_TILE)
            tiles.append(row)
        return cls(
            id=game_state.cur_map.id,
            ascii_tiles=tiles,
            known_sprites={},
            known_warps={},
        )

    @property
    def height(self) -> int:
        """The height of the map."""
        return len(self.ascii_tiles)

    @property
    def width(self) -> int:
        """The width of the map."""
        return len(self.ascii_tiles[0])

    def __str__(self) -> str:
        """Return a string representation of the map."""
        tiles = "\n".join("".join(row) for row in self.ascii_tiles)
        explored_percentage = np.mean(np.array(self.ascii_tiles) != UNSEEN_TILE)
        return OVERWORLD_MAP_STR_FORMAT.format(
            map_name=self.id.name,
            ascii_map=tiles,
            height=self.height,
            width=self.width,
            known_sprites=self._get_sprite_notes(),
            known_warps=self._get_warp_notes(),
            explored_percentage=f"{explored_percentage:.0%}",
        )

    async def save(self, parent_folder: Path) -> None:
        """Save the map to a file."""
        file_path = parent_folder / MAP_SUBFOLDER / f"{self.id.name}.json"
        async with aiofiles.open(file_path, "w") as f:
            await f.write(self.model_dump_json())

    def update_with_screen_info(self, game_state: YellowLegacyGameState) -> None:
        """Update the map with the screen info."""
        ascii_screen, sprites, warps = game_state.get_ascii_screen()
        self._add_tiles_to_screen(game_state.screen, ascii_screen)

        # TODO: Sprites need associated notes, not just positions.
        for s in sprites:
            if s.is_rendered:
                self.known_sprites[s.index] = s
            elif s.index in self.known_sprites:
                # Previously seen sprite has been de-rendered. Likely an item that has been picked
                # up, or a scripted character that has walked off screen.
                del self.known_sprites[s.index]

        for w in warps:
            self.known_warps[w.index] = w  # Warps are always rendered.

    def _add_tiles_to_screen(self, screen: ScreenState, ascii_screen: np.ndarray) -> None:
        """Add the tiles to the screen."""
        top = screen.top
        left = screen.left
        bottom = screen.bottom
        right = screen.right

        if top < 0:
            ascii_screen = ascii_screen[-top:]
            top = 0
        if left < 0:
            ascii_screen = ascii_screen[:, -left:]
            left = 0
        if bottom > self.height:
            ascii_screen = ascii_screen[: self.height - bottom]
            bottom = self.height
        if right > self.width:
            ascii_screen = ascii_screen[:, : self.width - right]
            right = self.width

        ascii_tiles = np.array(self.ascii_tiles)
        ascii_tiles[top:bottom, left:right] = ascii_screen
        self.ascii_tiles = ascii_tiles.tolist()

    def _get_sprite_notes(self) -> str:
        """Get the notes for the sprites on the map."""
        if not self.known_sprites:
            return "No sprites discovered."
        return "\n".join(
            [f"- {self.id.name}_{k} at ({v.y}, {v.x})" for k, v in self.known_sprites.items()]
        )

    def _get_warp_notes(self) -> str:
        """Get the notes for the warps on the map."""
        if not self.known_warps:
            return "No warp tiles discovered."
        return "\n".join(
            [f"- {self.id.name}_{k} at ({v.y}, {v.x})" for k, v in self.known_warps.items()]
        )
