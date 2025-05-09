from common import constants as c


OVERWORLD_MAP_STR_FORMAT = f"""
<map_info>
Map name: {{map_name}}
<map>
{{ascii_map}}
</map>
You have explored {{explored_percentage}} of this map.
<legend>
- {c.UNSEEN_TILE} - Tiles that you have not yet explored. Move towards these tiles to reveal them.
- {c.FREE_TILE} - A walkable tile with nothing noteworthy in it.
- {c.WALL_TILE} - A barrier that you cannot pass through.
- {c.CUT_TREE_TILE} - A tree.
- {c.WATER_TILE} - Water.
- {c.GRASS_TILE} - Tall grass, where wild Pokemon can be found.
- {c.LEDGE_TILE} - A ledge that you can jump down from above. These tiles are only passable if you approach them from above and walk downwards.
- {c.SPRITE_TILE} - A sprite that you can interact with. This could be an NPC, an item you can pick up, or some other interactable entity. You will need to use the screenshot to determine what the sprite is.
- {c.WARP_TILE} - A tile that can warp you to a different location. In the screenshot view, these are shown as doors, doormats, staircases, or teleporters.
- {c.PLAYER_TILE} - Your current location.
- {c.PIKACHU_TILE} - Your companion Pikachu. If you do not see this, it means that pikachu has either fainted or is not in your party.
</legend>

The map coordinates in row-column order start at (0, 0) in the top left corner, and increase to the right and down. The full size of the current map is {{height}}x{{width}} blocks. Note that the full size of the map is always represented in the ASCII map, even if you have not explored the entire map yet. The orientation of the map is also always fixed. Up is always up, and down is always down, regardless of the direction you are facing.

You have discovered the following sprites on the portion of the map that you have revealed so far:
<known_sprites>
{{known_sprites}}
</known_sprites>

You have discovered the following warp tiles on the portion of the map that you have revealed so far:
<known_warps>
{{known_warps}}
</known_warps>

Navigation tips:
- You should explore as much of the map as possible to reveal the unexplored tiles, as they may be hiding important sprites or warp tiles. Tiles are revealed by proximity to the player, so move towards the unexplored tiles to reveal them. Revealing unexplored tiles is always a good idea.
- Warp tiles come in two varieties: single and double.
  - Single warp tiles are activated by standing on them.
  - Double warp tiles (two warp tiles side by side) have to be walked through as if you're trying to walk off the edge of the map. These warp tiles are often on found on the edge of a map. (e.g. if you see a doube warp tile on the right edge of the map, you have to walk through it off the right edge of the map to enter the adjoining map.)
  - Do not attempt to interact with a warp tile using the action button. You have to walk on or through the tile depending on its type to warp.
- To connect from one map to another, you must either walk through a warp tile, or, *in outdoor maps only*, walk off the edge of the map.
- If you are indoors, the edges of the map (indicated by a black void in the screenshot) are impassable. You cannot walk off the edge of an indoor map. The only exception to this is if you see two adjacent warp tiles on the edge of a map. In this case, you can walk through the warp tiles to enter the adjoining map. Warp tiles are the only way to move between maps indoors.
- Your companion Pikachu will never block your movement. Unlike other sprites, you can walk through pikachu.
- To interact with a sprite, you need to be directly adjacent to it, face it, and press the action button. The only exception to the direct adjacency rule is in poke-marts and pokemon centers where you interact with the clerk or nurse respectively from across the counter that is directly in front of them.

Note that this ASCII map is significantly more reliable than the screenshot provided above. Screenshots can be misinterpreted, so use the ASCII map to determine the exact location of any sprites or tiles, and consider the screenshot as supplemental information to help you interpret the map.
</map_info>
""".strip()
