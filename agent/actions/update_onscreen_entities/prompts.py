UPDATE_SPRITES_PROMPT = """
There are one or more sprites visible on the screen right now. This is your chance to, if you so desire, update your long-term memory with new information about them.

{raw_memory}

{map_info}

The following sprites are visible on the screen right now. Here are the descriptions of them that you have in your long-term memory:
<sprites>
{sprites}
</sprites>

If you want to update your long-term memory with new information about any of these sprites, do so by returning an array of objects, where each object contains the sprite index (the one in square brackets above) and the new description. Do not include anything in your description about the position of the sprite; that information will be pulled from the game's memory as needed. Returning an empty array is a valid response and simply means that you don't want to update any of the sprite descriptions.

""".strip()

UPDATE_WARPS_PROMPT = """
There are one or more warp tiles visible on the screen right now. This is your chance to, if you so desire, update your long-term memory with new information about them.

{raw_memory}

{map_info}

The following warp tiles are visible on the screen right now. Here are the descriptions of them that you have in your long-term memory:
<warps>
{warps}
</warps>

If you want to update your long-term memory with new information about any of these warp tiles, do so by returning an array of objects, where each object contains the warp index (the one in square brackets above) and the new description. Do not include anything in your description about the position of the warp tile; that information will be pulled from the game's memory as needed. Returning an empty array is a valid response and simply means that you don't want to update any of the warp tile descriptions.
""".strip()
