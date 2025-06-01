MAKE_DECISION_PROMPT = """
You are navigating the overworld and there is no on-screen text. The screenshot provided above is the current game screen. You must decide which button to press or tool to use to proceed with the game.

The (case-sensitive) available buttons are:
- a: The action button. Used to interact with objects in the game. The object you interact with will be the tile directly adjacent to you in the direction that you are facing.
- start: Used to open the main menu.
- up: Used to move the character upwards.
- down: Used to move the character downwards.
- left: Used to move the character left.
- right: Used to move the character right.

You also have access to the navigation tool, which can be used to navigate to any revealed, accessible tile on the current map. To use this tool, simply provide the coordinates of the tile you wish to navigate to in the "navigation_args" field below. Navigation from one map to another is not possible using this tool, but you can navigate to the edge of the current map and then transition from this map to the next in the next iteration using the directional buttons. You may also use the navigation tool to navigate directly to any accessible warp tile that you have discovered on the current map. The navigation tool will update your map information as you navigate, so think of it as a more efficient way to move around if you want to move more than one tile at a time. The navigation tool can be used to navigate beyond the current screen as well, but only as far as the edge of the current map. It is generally recommended to use the navigation tool if you want to move more than one tile.
For reference, the walkable tiles types are {walkable_tiles}.

{agent_memory}

{goals}

{player_info}

The following is an ASCII representation of the current map, highlighting your current location. Note that the screenshot above, also represented in ASCII below, is only a subset of the current map, centered on your current location.
{current_map}

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your written thoughts on the current game state and which button to press. Use the following thought process, and be thorough in your commentary:
    1. Consider your goals. What are you trying to accomplish?
    2. Consider the information provided in the raw memory. What has happened lately? If you feel like you're repeating yourself, or getting stuck in a loop, say so, and suggest a change of course.
    3. Consider the player information provided to you. What is your current situation?
    4. Consider the map information provided to you. Where are you, and where do you want to go? Are there sprites or warp tiles that you haven't checked out yet? Is there something blocking your path?
    5. Consider the screenshot. What is currently on the screen? How does it help you contextualize your situation?
    6. Synthesize the above information, and decide which button to press.
- button: The button to press, if applicable. Must be one of the available buttons above.
- navigation_args: The coordinates to navigate to, if applicable.

Exactly one of "button" or "navigation_args" must be provided.
""".strip()
