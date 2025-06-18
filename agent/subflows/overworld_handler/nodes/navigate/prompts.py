DETERMINE_TARGET_COORDS_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You have decided to navigate to a new location on the current map.

{state}

This navigation tool can be used to navigate to any revealed, accessible tile on the current map using an A* search algorithm by simply providing the desired coordinates. The navigation tool can be used to navigate beyond the current screen, but only as far as the edge of the current map. Navigation from one map to another is not possible using this tool, but you can navigate to the edge of the current map and then transition from this map to the next in the next iteration. You may also use the navigation tool to navigate directly to any accessible warp tile that you have discovered on the current map.

The coordinates accessible to you from your current position are as follows:
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

Your most recent raw memory is repeated below for reference. The "thoughts" in your response will be appended to the end of this memory:
<memory>
{last_memory}
</memory>
If you see coordinates in the <memory> section, do not treat them as mandatory. The full list of accessible coordinates was not available to you when you generated the memory, and you thus may have generated coordinates that are not accessible. Determine what the memory is trying to tell you and choose the best coordinates from the list of accessible coordinates above. Choosing inaccessible coordinates will result in an error.

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your brief thoughts on where you would like to navigate to and why.
- coords: The row-column coordinates of the tile you would like to navigate to. Must be one of the accessible coordinates provided above.
""".strip()
