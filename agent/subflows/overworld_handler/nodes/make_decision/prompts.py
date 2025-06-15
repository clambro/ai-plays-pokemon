MAKE_DECISION_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You must decide which of the available tools to use to proceed with the game.

{state}

The first tool at your disposal is the button tool, which can be used to press any of the following (case-sensitive) buttons:
- a: The action button. Used to interact with objects in the game. The object you interact with will be the tile directly adjacent to you in the direction that you are facing.
- start: Used to open the main menu.
- up: Used to move the player upwards.
- down: Used to move the player downwards.
- left: Used to move the player left.
- right: Used to move the player right.

You also have access to the navigation tool, which can be used to navigate to any revealed, accessible tile on the current map using an A* search algorithm. To use this tool, simply provide the coordinates of the tile you wish to navigate to in the "navigation_args" field below. The navigation tool can be used to navigate beyond the current screen, but only as far as the edge of the current map. Navigation from one map to another is not possible using this tool, but you can navigate to the edge of the current map and then transition from this map to the next in the next iteration using the directional buttons. You may also use the navigation tool to navigate directly to any accessible warp tile that you have discovered on the current map. Think of it as a more efficient way to move around if you want to move more than one tile at a time. It is generally recommended to use the navigation tool if you want to move more than one tile. Conversely, it is somewhat pointless to use the navigation tool to move a single tile. If you are having trouble moving around obstacles or through winding paths, the navigation tool can probably help you.
For reference, the walkable tiles types are {walkable_tiles}.

The following explored, walkable tiles are adjacent to unseen territory on the current map. They are therefore top candidates for exploration using the navigation tool. Note that it is not guaranteed that all of these tiles are accessible, but the navigation tool will inform you if you try to navigate to an inaccessible tile. If the section below is empty, then you have already explored all of the tiles on the current map. Using the navigation tool to navigate to these exploration candidates is the most efficient way to explore the current map.
<exploration_candidates>
{exploration_candidates}
</exploration_candidates>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your written thoughts on the current game state and which tool to use in response. Use the following thought process, and be thorough in your commentary:
    1. Consider your goals. What are you trying to accomplish?
    2. Consider the information provided in the raw memory. What has happened lately? If you feel like you're repeating yourself, or getting stuck in a loop, say so, and suggest a change of course.
    3. Consider the player information provided to you. What is your current situation?
    4. Consider the map information provided to you. Where are you, and where do you want to go? Are there sprites you haven't interacted with yet? Is there unexplored territory that you can navigate to?
    5. Consider the screenshot. What is currently on the screen? How does it help you contextualize your situation?
    6. Synthesize the above information, and decide which of the tools below to use in response.
- buttons: The button(s) to press, if applicable. This can be a single button, or a list of buttons to be pressed in sequence. You should generally prefer to press a single button at a time, but you can use a combination of buttons to, say, rotate the player and then interact with an object. Prefer the navigation tool over multiple button presses for moving around.
- navigation_args: The coordinates to navigate to, if applicable.

Exactly one of "buttons" or "navigation_args" must be provided. You must pick a tool to use. You are not in a cutscene or battle or reading text. You are standing still in the overworld, and the game is awaiting your input, so doing nothing is not an option.
""".strip()
