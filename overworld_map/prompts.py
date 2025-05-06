from common import constants as c


OVERWORLD_MAP_STR_FORMAT = f"""
{{map_name}}:
<map>
{{ascii_map}}
</map>
<legend>
{c.UNSEEN_TILE} - Unexplored terrain.
{c.FREE_TILE} - A walkable tile with nothing noteworthy in it.
{c.WALL_TILE} - A barrier that you cannot pass through.
{c.CUT_TREE_TILE} - A tree.
{c.WATER_TILE} - Water.
{c.GRASS_TILE} - Tall grass ,where wild Pokemon can be found.
{c.LEDGE_TILE} - A ledge that you can jump down from above. These tiles are only passable if you approach them from above and walk downwards.
{c.SPRITE_TILE} - A sprite that you can interact with. This could be an NPC, an item you can pick up, or some other interactable entity. You will need to use the screenshot to determine what the sprite is. To interact with a sprite, you need to be directly adjacent to it, face it, and press the action button. You can only determine the direction you are facing by using the screenshot. The only exception to the direct adjacency rule is in poke-marts and pokemon centers where you interact with the clerk or nurse respectively from across the counter that is directly in front of them.
{c.WARP_TILE} - A tile that can warp you to a different location. It is usually a door, though it could be a teleporter. Note that if you see two adjacent warp tiles on the edge of a map, you have to walk through them to warp. Single warp tiles are activated by standing on them, but doubles have to be walked through.
{c.PLAYER_TILE} - Your current location.
{c.PIKACHU_TILE} - Your companion Pikachu. If you do not see this, it means that pikachu has either fainted or is not in your party. Note that pikachu will never block your movement. Unlike other sprites, you can walk through pikachu.
</legend>

The map coordinates in row-column order start at (0, 0) in the top left corner, and increase to the right and down. The full map size is {{height}}x{{width}} blocks.
""".strip()
