UPDATE_SPRITES_PROMPT = """
There are one or more sprites visible on the screen right now. This is your chance to, if you so desire, update your long-term memory with new information about them.

{state}

The following sprites are visible on the screen right now. Here are the descriptions of them that you have in your long-term memory:
<sprites>
{entities}
</sprites>

Sprites are usually either people or item balls, but can also be other objects or Pokemon. You should note the kind of sprite in your description, as well as any other relevant information about it. If the sprite is a person, whom you have recently spoken to, you should note what they said in the description of the sprite.

Do not assume anything about who or what a sprite is until you have interacted with it. Your vision via the screenshot is unreliable. Be explicit about not knowing in your description so that you will know to update your description when you learn more. The best way to learn more is to interact with the sprite using the action button.

If you want to update your long-term memory with new information about any of these sprites, do so by returning an array of objects, where each object contains the sprite index (the one in square brackets above) and the new description. Do not include anything in your description about the position of the sprite; that information will be pulled from the game's memory as needed. Returning an empty array is a valid response and simply means that you don't want to update any of the sprite descriptions. If you have not learned anything new about any of the sprites, you should not update any of the descriptions.
""".strip()

UPDATE_WARPS_PROMPT = """
There are one or more warp tiles visible on the screen right now. This is your chance to, if you so desire, update your long-term memory with new information about them.

{state}

The following warp tiles are visible on the screen right now. Here are the descriptions of them that you have in your long-term memory:
<warps>
{entities}
</warps>

For warp tiles, it's important to note the kind of warp tile in your description: single vs double.
- Single warp tiles are activated by standing on them.
- Double warp tiles (two warp tiles side by side) are usually found on the edge of a map, and have to be walked through perpendicularly over the edge of the map. (e.g. if you see a doube warp tile arranged vertically on the right edge of the map, you have to stand on one of the tiles and walk right, off the edge of the map; if you see a double warp tile arranged horizontally on the bottom edge of the map, you have to stand on one of the tiles and walk down, off the edge of the map; etc.). If you see a double warp tile, you should note that it is a double warp tile in your description, as well as noting the direction you have to walk through it to warp.
- Warp tiles are never interacted with using the action button. You have to walk on or through the tile depending on its type to warp.

You do not need to re-add this information if it is already present, but you can update your description if you have learned something new about a warp tile. If you find yourself on a double warp tile and not getting anywhere, check to make sure that you have not misinterpreted the direction that you have to walk through the tile to warp.

The warp tile will tell you which map it leads to, but no more information than that. Do not assume anything about the details of where a warp tile will take you unless you know for sure based on the information provided. Be explicit about not knowing in your description so that you will know to update your description when you learn more. The best way to learn more is to use the warp tile and see where it takes you.

If you want to update your long-term memory with new information about any of these warp tiles, do so by returning an array of objects, where each object contains the warp index (the one in square brackets above) and the new description. Do not include anything in your description about the position of the warp tile; that information will be pulled from the game's memory as needed. Returning an empty array is a valid response and simply means that you don't want to update any of the warp tile descriptions. If you have not learned anything new about any of the warp tiles, you should not update any of the descriptions.
""".strip()

UPDATE_SIGNS_PROMPT = """
There are one or more signs visible on the screen right now. This is your chance to, if you so desire, update your long-term memory with new information about them.

{state}

The following signs are visible on the screen right now. Here are the descriptions of them that you have in your long-term memory:
<signs>
{entities}
</signs>

Signs are usualy either signposts or TVs, but can be other objects. Their key defining feature is that they are static, unchanging places where you can read some informational text. You should note the kind of sign in your description, as well as any other relevant information about it. If you have recently read the text on a sign, you should note that in your description.

Do not assume anything about what the text on a sign says unless you know for sure based on the information provided. Be explicit about not knowing in your description so that you will know to update your description when you learn more. The best way to learn more is to interact with the sign using the action button.

If you want to update your long-term memory with new information about any of these signs, do so by returning an array of objects, where each object contains the sign index (the one in square brackets above) and the new description. Do not include anything in your description about the position of the sign; that information will be pulled from the game's memory as needed. Returning an empty array is a valid response and simply means that you don't want to update any of the sign descriptions. If you have not learned anything new about any of the signs, you should not update any of the descriptions.
""".strip()
