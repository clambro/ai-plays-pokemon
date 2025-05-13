from pathlib import Path

GAME_TICKS_PER_SECOND = 60

SCREEN_HEIGHT = 9
SCREEN_WIDTH = 10
PLAYER_OFFSET_Y = 4
PLAYER_OFFSET_X = 4

# TODO: This should be an enum.
UNSEEN_TILE = "?"
WALL_TILE = "x"
WATER_TILE = "~"
GRASS_TILE = "*"
LEDGE_TILE = "-"
FREE_TILE = "."
PLAYER_TILE = "P"
SPRITE_TILE = "S"
WARP_TILE = "W"
CUT_TREE_TILE = "T"
PIKACHU_TILE = "k"

RAW_MEMORY_MAX_SIZE = 100

OUTPUTS_FOLDER = Path("outputs/")
MAP_SUBFOLDER = "maps"
SPRITE_SUBFOLDER = "sprites"
WARP_SUBFOLDER = "warps"

DB_FILE_PATH = OUTPUTS_FOLDER / "database" / "memory.db"
DB_URL = f"sqlite+aiosqlite:///{DB_FILE_PATH}"
