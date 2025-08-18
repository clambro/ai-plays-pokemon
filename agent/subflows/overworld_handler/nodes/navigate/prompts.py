DETERMINE_TARGET_COORDS_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You have decided to navigate to a new location on the current map.

{state}

This navigation tool can be used to navigate to any revealed, accessible tile on the current map using an A* search algorithm by simply providing the desired coordinates. The navigation tool can be used to navigate beyond the current screen, but only as far as the edge of the current map. Navigation from one map to another is not possible using this tool, but you can navigate to the edge of the current map and then transition from this map to the next in the next iteration. You may also use the navigation tool to navigate directly to any accessible warp tile that you have discovered on the current map.

The coordinates accessible from your current position are as follows:
<accessible_coords>
{accessible_coords}
</accessible_coords>

The following accessible coordinates (a subset of the accessible coordinates provided above) are adjacent to unseen territory on the current map. They are therefore top candidates for exploration. If the section below is empty, then you have already explored all of the accessible tiles on the current map. Navigating towards any of these coordinates is the most efficient way to explore the current map.
<exploration_candidates>
{exploration_candidates}
</exploration_candidates>

If there are maps connected to the current map, the following section will guide you on how to navigate to the boundaries of the current map so that you can transition to the next map in the next iteration if you choose to do so. If this section is empty, it means that the current map is not connected to any other maps and has to be exited via warp tiles.
<map_boundaries>
{map_boundaries}
</map_boundaries>

Your most recent raw memory is repeated below for reference. The "thoughts" in your response will be appended verbatim to the end of this memory, so there is no need to duplicate information.
<last_memory>
{last_memory}
</last_memory>
Pay close attention to the intent expressed in your last memory. When that memory was generated, you did not have access to the coordinates provided above. This means that in rare cases you can override nonsensical requests in the last memory. Some rules for this:
- If the last memory asks you to navigate to a specific warp, boundary, or location, and that location is accessible, you MUST follow the last memory's request and navigate directly to that location.
- If the last memory intends to interact with a sprite, sign, or some other object, you must move to an accessible coordinate adjacent to that object.
- If the last memory asks you to navigate to an inaccessible coordinate, you must override it with an accessible coordinate.
- If the last memory indicates a desire to explore the map or find exploration candidates, you MUST select one of the exploration candidates (even if it is not the exact coordinate you were asked to navigate to). The only exception is if there are no exploration candidates available, in which case you should mention that fact.
- If the last memory asks you to explore the map but gives you an inaccessible target, or an area that you have already explored, you must override it with an accessible exploration candidate. Again, the only exception is if there are no exploration candidates available, in which case you should mention that fact.
- When in doubt, prioritize exploration candidates over accessible coordinates.

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your one sentence long thoughts on which coordinates you would like to navigate to given the information provided. These thoughts will be appended verbatim to the end of the <last_memory> in your raw memory. If you are overriding the last memory's request, mention that here and briefly explain why you are doing so.
- coords: The row-column coordinates of the tile you would like to navigate to. Must be one of the accessible coordinates provided above.
""".strip()
