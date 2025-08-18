DETERMINE_TARGET_COORDS_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You have decided to navigate to a new location on the current map.

{state}

This navigation tool can be used to navigate to any revealed, accessible tile on the current map using an A* search algorithm by simply providing the desired coordinates. The navigation tool can be used to navigate beyond the current screen, but only as far as the edge of the current map. Navigation from one map to another is not possible using this tool, but you can navigate to the edge of the current map and then transition from this map to the next in the next iteration. You may also use the navigation tool to navigate directly to any accessible warp tile that you have discovered on the current map.

The coordinates accessible from your current position are as follows:
<accessible_coords>
{accessible_coords}
</accessible_coords>

The following accessible coordinates (a subset of the accessible coordinates provided above) are adjacent to unseen territory on the current map. They are therefore top candidates for exploration. If the section below is empty, then you have already explored all of the accessible tiles on the current map. Navigating towards any of these coordinates is the most efficient way to explore the current map. If your last memory asks you to explore the map, you should choose one of these exploration candidates.
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
If you see coordinates in the <last_memory> section, do not treat them as mandatory. The full list of accessible coordinates and exploration candidates was not available to you when you generated the memory, and you thus may have requested incorrect coordinates. You have a lot more information available to you in this prompt than you did when the last memory was generated, so you are allowed to overrule it if the request does not make sense (e.g. if you wanted to explore unseen territory on the west side of the current map but you now see that the exploration candidates are all on the south side, you would have to mention that fact and decide what to do about it). Determine what the memory is trying to tell you and choose the best coordinates from the list above. Choosing inaccessible coordinates will result in an error.

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your one sentence long thoughts on which coordinates you would like to navigate to given the information provided. These thoughts will be appended verbatim to the end of the <last_memory> in your raw memory. If you made a mistake in your last memory, mention it here and correct it.
- coords: The row-column coordinates of the tile you would like to navigate to. Must be one of the accessible coordinates provided above.
""".strip()
