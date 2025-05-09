from pathlib import Path
import aiofiles
from loguru import logger
import numpy as np
from typing import Self

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from pyboy import PyBoyMemoryView
from pydantic import BaseModel

from emulator.enums import FacingDirection, MapLocation


class PlayerState(BaseModel):
    """The state of the player character."""

    is_moving: bool
    y: int
    x: int
    direction: FacingDirection
    money: int

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new player state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the player state from.
        :return: A new player state.
        """
        is_moving = mem[0xC107] + mem[0xC108] != 0
        return cls(
            is_moving=is_moving,
            y=mem[0xD3AE],
            x=mem[0xD3AF],
            direction=FacingDirection(mem[0xD577]),
            money=cls._read_money(mem),
        )

    @staticmethod
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


class Sprite(BaseModel):
    """A sprite on the current map."""

    index: int
    y: int
    x: int
    is_rendered: bool

    async def get_description(self, sprite_folder: Path, map_id: MapLocation) -> str:
        """Get a description of the sprite from a file."""
        file_path = sprite_folder / f"sprite_{map_id.value}_{self.index}.txt"
        if not file_path.exists():
            return "No description added yet."
        async with aiofiles.open(file_path) as f:
            data = await f.read()
        return data

    async def save_description(
        self, sprite_folder: Path, map_id: MapLocation, description: str
    ) -> None:
        """Save a description of the sprite to a file."""
        logger.info(f"Updating sprite_{map_id.value}_{self.index} with description: {description}")
        file_path = sprite_folder / f"sprite_{map_id.value}_{self.index}.txt"
        async with aiofiles.open(file_path, "w") as f:
            await f.write(description)


class Warp(BaseModel):
    """A warp on the current map."""

    index: int
    y: int
    x: int

    async def get_description(self, warp_folder: Path, map_id: MapLocation) -> str:
        """Get a description of the warp from a file."""
        file_path = warp_folder / f"warp_{map_id.value}_{self.index}.txt"
        if not file_path.exists():
            return "No description added yet."
        async with aiofiles.open(file_path) as f:
            data = await f.read()
        return data

    async def save_description(
        self, warp_folder: Path, map_id: MapLocation, description: str
    ) -> None:
        """Save a description of the warp to a file."""
        logger.info(f"Updating warp_{map_id.value}_{self.index} with description: {description}")
        file_path = warp_folder / f"warp_{map_id.value}_{self.index}.txt"
        async with aiofiles.open(file_path, "w") as f:
            await f.write(description)


class MapState(BaseModel):
    """The state of the current map."""

    id: MapLocation
    tileset_id: int
    height: int
    width: int
    grass_tile: int
    water_tile: int
    ledge_tiles: list[int]
    cut_tree_tiles: list[int]
    walkable_tiles: list[int]
    sprites: list[Sprite]
    pikachu_sprite: Sprite
    warps: list[Warp]

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new map state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the map state from.
        :return: A new map state.
        """
        tileset_id = mem[0xD3B4]

        # These two were found by inspection.
        ledge_tiles = [54, 55] if tileset_id == 0 else []
        cut_tree_tiles = [45, 46, 61, 62] if tileset_id == 0 else []

        walkable_tile_ptr = mem[0xD57D] | (mem[0xD57E] << 8)
        walkable_tiles = []
        for i in range(0x180):  # Max possible unique tiles.
            if mem[walkable_tile_ptr + i] == 0xFF:  # Memory section is terminated by 0xFF.
                break
            walkable_tiles.append(mem[walkable_tile_ptr + i])

        sprites, pikachu_sprite = cls._get_sprites(mem)

        return cls(
            id=MapLocation(mem[0xD3AB]),
            tileset_id=mem[0xD3B4],
            height=mem[0xD571],
            width=mem[0xD572],
            grass_tile=mem[0xD582],
            water_tile=mem[3, 0x68A5],
            ledge_tiles=ledge_tiles,
            cut_tree_tiles=cut_tree_tiles,
            walkable_tiles=walkable_tiles,
            sprites=sprites,
            pikachu_sprite=pikachu_sprite,
            warps=cls._get_warps(mem),
        )

    @staticmethod
    def _get_sprites(mem: PyBoyMemoryView) -> tuple[list[Sprite], Sprite]:
        """
        Get the list of sprites on the current map from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the sprites from.
        :return: A list of normal sprites, plus the pikachu sprite.
        """
        sprites = []
        for i in range(0x10, 0xF0, 0x10):  # First sprite is the player.
            if mem[0xC100 + i] == 0:  # No more sprites on this map.
                break
            sprites.append(
                Sprite(
                    index=i,
                    # Sprite coordinates start counting from 4 for some reason.
                    y=mem[0xC204 + i] - 4,
                    x=mem[0xC205 + i] - 4,
                    is_rendered=mem[0xC102 + i] != 0xFF,
                )
            )
        pikachu_sprite = Sprite(
            index=0,
            y=mem[0xC2F4] - 4,
            x=mem[0xC2F5] - 4,
            is_rendered=mem[0xC1F2] != 0xFF,
        )
        return sprites, pikachu_sprite

    @staticmethod
    def _get_warps(mem: PyBoyMemoryView) -> list[Warp]:
        """
        Get the list of warps on the current map from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the warps from.
        :return: A list of warps.
        """
        num_warps = mem[0xD3FB]
        warps = []
        for i in range(num_warps):
            base = 0xD3FC + 4 * i
            warps.append(Warp(index=i, y=mem[base], x=mem[base + 1]))
        return warps


class ScreenState(BaseModel):
    """The state of the screen."""

    top: int
    left: int
    bottom: int
    right: int

    # Each block on screen is a 2x2 square of tiles.
    tiles: list[list[int]]

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new screen state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the screen state from.
        :return: A new screen state.
        """
        player_y = mem[0xD3AE]
        player_x = mem[0xD3AF]

        top = player_y - PLAYER_OFFSET_Y
        left = player_x - PLAYER_OFFSET_X
        bottom = top + SCREEN_HEIGHT
        right = left + SCREEN_WIDTH

        shape = (SCREEN_HEIGHT * 2, SCREEN_WIDTH * 2)
        tiles = np.asarray(mem[0xC3A0:0xC508]).reshape(shape).tolist()

        return cls(
            top=top,
            left=left,
            bottom=bottom,
            right=right,
            tiles=tiles,
        )

    def get_screen_coords(self, y: int, x: int) -> tuple[int, int] | None:
        """
        Convert global coordinates to screen coordinates.

        :param y: The global y coordinate.
        :param x: The global x coordinate.
        :return: The screen coordinates (y, x) or None if they're off screen.
        """
        if y < self.top or y >= self.bottom or x < self.left or x >= self.right:
            return None
        return (y - self.top, x - self.left)


class BattleState(BaseModel):
    """The state of the current battle."""

    is_in_battle: bool

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new battle state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the battle state from.
        :return: A new battle state.
        """
        return cls(is_in_battle=bool(mem[0xD057]))
