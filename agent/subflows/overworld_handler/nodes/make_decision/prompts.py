MAKE_DECISION_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You must decide which of the available tools to use to proceed with the game.

{state}

You have the following tools at your disposal:
<tools>
<button_tool>
The button tool allows you to submit one or more button presses to the emulator. It is useful for:
- Interacting with entities in the game.
- Opening the main menu.
- Rotating the player.
- Moving the player one or two tiles at a time.
- Transitioning from one map to another if you are at the edge of the current map or near a warp tile.

Give general guidance on which buttons to press in your thoughts, but do not provide specific button presses. The tool will determine the legal button presses and prompt you again to choose from them.
</button_tool>
<navigation_tool>
The navigation tool allows you to navigate to any revealed, accessible tile on the current map using an A* search algorithm. It is useful for:
- Moving the player around the current map more than one tile at a time.
- Navigating directly to warp tiles.
- Revealing unexplored territory on the current map.

Give general guidance on where you want to go in your thoughts, but do not provide specific coordinates. The tool will determine the legal navigation targets and prompt you again to choose from them.
</navigation_tool>
</tools>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your written thoughts on the current game state and which tool to use in response. Use the following thought process, and be thorough in your commentary:
    1. Consider your goals. What are you trying to accomplish?
    2. Consider the information provided in the raw memory. What has happened lately? If you feel like you're repeating yourself, or getting stuck in a loop, say so, and suggest a change of course.
    3. Consider the player information provided to you. What is your current situation?
    4. Consider the map information provided to you. Where are you, and where do you want to go? Are there sprites you haven't interacted with yet? Is there unexplored territory that you can navigate to?
    5. Consider the screenshot. What is currently on the screen? How does it help you contextualize your situation?
    6. Synthesize the above information, and decide which of the tools below to use in response.
- tool: The tool to use. Must be one of the tools listed above. The JSON description below may name tools that are not described above. Ignore them. The only valid tools are the ones listed above in the <tools> section.
""".strip()
