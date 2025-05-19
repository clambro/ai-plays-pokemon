from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from common.enums import AsciiTiles

OVERWORLD_MAP_STR_FORMAT = f"""
<map_info>
Map name: {{map_name}}
<ascii_screen>
{{ascii_screen}}
</ascii_screen>
<whole_map>
{{ascii_map}}
</whole_map>
You have explored {{explored_percentage}} of this map.
<legend>
- "{AsciiTiles.UNSEEN}" - Tiles that you have not yet explored. Move toward these tiles to reveal them.
- "{AsciiTiles.FREE}" - A walkable tile with nothing noteworthy in it.
- "{AsciiTiles.WALL}" - A barrier (usually a wall or an object) that you cannot pass through.
- "{AsciiTiles.CUT_TREE}" - A tree.
- "{AsciiTiles.WATER}" - Water.
- "{AsciiTiles.GRASS}" - Tall grass, where wild Pokemon can be found.
- "{AsciiTiles.LEDGE}" - A ledge that you can jump down from above. These tiles are only passable if you approach them from above and walk downwards.
- "{AsciiTiles.SPRITE}" - A sprite that you can interact with. This could be an NPC, an item you can pick up, or some other interactable entity. You will need to use the screenshot to determine what the sprite is. You cannot walk through sprites, nor can you stand on top of them.
- "{AsciiTiles.WARP}" - A tile that can warp you to a different location. In the screenshot view, these are shown as doors, doormats, staircases, or teleporters.
- "{AsciiTiles.PLAYER}" - Your current location.
- "{AsciiTiles.PIKACHU}" - Your companion Pikachu that follows you around. May or may not be present on the map. Pikachu will always be standing on a walkable tile if present.
- "{AsciiTiles.SIGN}" - An object that you can interact with to read something. Usually a signpost, but could be a TV, radio, or other object. The main distinction between signs and sprites is that signs are static. They will never move, and their text will never change.
</legend>

The map coordinates in row-column order start at (0, 0) in the top left corner. The rows increase from top to bottom, and the columns increase from left to right. The full size of the current map is {{height}}x{{width}} blocks.

The ASCII screen is always ({SCREEN_HEIGHT}x{SCREEN_WIDTH}) blocks in size, and is always centered such that the player is in position ({PLAYER_OFFSET_Y}, {PLAYER_OFFSET_X}) in screen coordinates (not map coordinates). It corresponds 1:1 with the screenshot provided to you above. Note that the screen can extend outside the boundaries of the whole map section. This should help you navigate from one map to another. The upper left corner of the screen is currently at ({{screen_upper_left_y}}, {{screen_upper_left_x}}) in map coordinates. The lower right corner of the screen is currently at ({{screen_lower_right_y}}, {{screen_lower_right_x}}) in map coordinates.

The tile directly above you is "{{tile_above}}".
The tile directly below you is "{{tile_below}}".
The tile directly to the left of you is "{{tile_left}}".
The tile directly to the right of you is "{{tile_right}}".

You have discovered the following sprites on the portion of the map that you have revealed so far:
<known_sprites>
{{known_sprites}}
</known_sprites>

You have discovered the following warp tiles on the portion of the map that you have revealed so far:
<known_warps>
{{known_warps}}
</known_warps>

You have discovered the following signs on the portion of the map that you have revealed so far:
<known_signs>
{{known_signs}}
</known_signs>

Navigation tips:
- You should explore as much of the map as possible to reveal the unexplored tiles, as they may be hiding important sprites or warp tiles. Tiles are considered explored once they are on screen, so move towards the unexplored tiles to reveal them.
- Exploring the map to reveal unexplored tiles is always a good idea, especially if you feel stuck or unsure of how to proceed.
- The orientation of the map and screen are always fixed, regardless of the direction that you are facing.
- Warp tiles come in two varieties: single and double.
  - Single warp tiles are activated by standing on them. If you are standing on a warp tile and not going anywhere, it means that you have just warped to this tile from somewhere else. If you want to go back to your previous location and are standing on a single warp tile, you have to walk off the tile and then back on it to warp back.
  - Double warp tiles (two warp tiles side by side) are more complicated. These tiles are usually found on the edge of a map, and have to be walked through as if you're trying to walk off the edge of the map, into the barrier. (e.g. if you see a doube warp tile arranged vertically on the right edge of the map, you have to stand on one of the tiles and walk right, off the edge of the map; if you see a double warp tile arranged horizontally on the bottom edge of the map, you have to stand on one of the tiles and walk down, off the edge of the map; etc.). This is the only instance in which you are allowed to walk on a barrier tile.
  - If you find yourself on a double warp tile and are not getting anywhere, try walking into an adjacent tile of type "{AsciiTiles.WALL}" to exit the map.
  - Do not attempt to interact with a warp tile using the action button. You have to walk on or through the tile depending on its type to warp..
- To connect from one map to another, you must either walk through a warp tile, or, *in outdoor maps only*, walk off the edge of the map. Trust the ASCII screen to guide you between maps outdoors.
- If you are indoors, the edges of the map (indicated by a black void in the screenshot) are impassable. You cannot walk off the edge of an indoor map. The only exception to this is if you see two adjacent warp tiles on the edge of a map. In this case, you can walk through the warp tiles to enter the adjoining map. Warp tiles are the only way to move between maps indoors.
- Your companion Pikachu will never block your movement. Unlike other sprites, you can walk through pikachu.
- To interact with a sprite, you need to be directly adjacent to it, face it, and press the action button. The only exception to the direct adjacency rule is in poke-marts and pokemon centers where you interact with the clerk or nurse respectively from across the counter that is directly in front of them.
- Note that some sprites move around, so their position may change between screenshots. Do not let this confuse you. The information that you have in the <known_sprites> section is the most accurate information available to you since it comes straight from the game's memory at this moment in time.

Note that this ASCII information comes straight from the game's memory and is therefore perfectly reliable. Screenshot images can be misinterpreted, so use the ASCII map and screen to determine the exact location of any sprites or tiles, and consider the screenshot image as supplemental information to help you visually interpret the ASCII.
</map_info>
""".strip()
