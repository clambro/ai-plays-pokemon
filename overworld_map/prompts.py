from common import constants as c


OVERWORLD_MAP_STR_FORMAT = f"""
<map_info>
{{map_name}}:
<map>
{{ascii_map}}
</map>
<legend>
- {c.UNSEEN_TILE} - Tiles that you have not yet explored. Move towards these tiles to reveal them.
- {c.FREE_TILE} - A walkable tile with nothing noteworthy in it.
- {c.WALL_TILE} - A barrier that you cannot pass through.
- {c.CUT_TREE_TILE} - A tree.
- {c.WATER_TILE} - Water.
- {c.GRASS_TILE} - Tall grass, where wild Pokemon can be found.
- {c.LEDGE_TILE} - A ledge that you can jump down from above. These tiles are only passable if you approach them from above and walk downwards.
- {c.SPRITE_TILE} - A sprite that you can interact with. This could be an NPC, an item you can pick up, or some other interactable entity. You will need to use the screenshot to determine what the sprite is.
- {c.WARP_TILE} - A tile that can warp you to a different location. It is usually a door, though it could be a teleporter.
- {c.PLAYER_TILE} - Your current location.
- {c.PIKACHU_TILE} - Your companion Pikachu. If you do not see this, it means that pikachu has either fainted or is not in your party.
</legend>

The map coordinates in row-column order start at (0, 0) in the top left corner, and increase to the right and down. The full size of the current map is {{height}}x{{width}} blocks.

Navigation tips:
- You should explore as much of the map as possible to reduce the number of unexplored tiles. Tiles are revealed by proximity to the player, so the only way to reveal the map is to explore it yourself.
- Warp tiles come in two varieties: single and double.
  - Single warp tiles are activated by standing on them.
  - Double warp tiles (two warp tiles side by side) have to be walked through. These warp tiles are often on found on the edge of a map.
  - Do not attempt to interact with a warp tile using the action button. You have to walk on or through the tile depending on its type to warp.
- Outdoors, all maps are surrounded by barrier tiles. Gaps in these barriers are the connectors between maps.
- Indoors, barriers are often omitted in the ASCII map. If you are indoors, assume that the edges of the map are the barriers. You cannot walk off the edge of an indoor map (indicated by a black void in the screenshot). The only exception to this is if you see two adjacent warp tiles on the edge of a map. In this case, you can walk through the warp tiles and off the edge of the map to enter the adjoining map. Warp tiles are the only way to move between maps indoors.
- Your companion Pikachu will never block your movement. Unlike other sprites, you can walk through pikachu.
- To interact with a sprite, you need to be directly adjacent to it, face it, and press the action button. You can only determine the direction you are facing by using the screenshot. The only exception to the direct adjacency rule is in poke-marts and pokemon centers where you interact with the clerk or nurse respectively from across the counter that is directly in front of them.

Note that this ASCII map is significantly more reliable than the screenshot provided above. Screenshots can be misinterpreted, so use the ASCII map to determine the exact location of any sprites or tiles, and consider the screenshot as supplemental information to help you interpret the map.
</map_info>
""".strip()
