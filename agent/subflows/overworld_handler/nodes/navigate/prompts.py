DETERMINE_TARGET_COORDS_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You have decided to navigate to a new location on the current map.

{state}

This navigation tool can be used to navigate to any revealed, accessible tile on the current map using an A* search algorithmby simply providing the desired coordinates. The navigation tool can be used to navigate beyond the current screen, but only as far as the edge of the current map. Navigation from one map to another is not possible using this tool, but you can navigate to the edge of the current map and then transition from this map to the next in the next iteration. You may also use the navigation tool to navigate directly to any accessible warp tile that you have discovered on the current map. For reference, the walkable tiles types are {walkable_tiles}.

The following explored, walkable tiles are adjacent to unseen territory on the current map. They are therefore top candidates for exploration using the navigation tool. Note that it is not guaranteed that all of these tiles are accessible, but the tool will inform you if you try to navigate to an inaccessible tile. If the section below is empty, then you have already explored all of the accessible tiles on the current map. Using the navigation tool to navigate to these exploration candidates is the most efficient way to explore the current map.
<exploration_candidates>
{exploration_candidates}
</exploration_candidates>

Your most recent raw memory is repeated below for reference. The "thoughts" in your response will be appended to the end of this memory:
<memory>
{last_memory}
</memory>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your brief thoughts on where you would like to navigate to and why.
- coords: The row-column coordinates of the tile you would like to navigate to.
""".strip()
