SELECT_TOOL_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You must decide which of the available tools to use to proceed with the game.

{state}

You have the following tools at your disposal:
<tools>
{tools}
</tools>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your brief thoughts on the current game state and which tool that you would like to use. Your reasoning should be concise and based on the uses listed for the tools above.
- tool: The tool to use. The only valid tools are the ones listed above in the <tools> section, and the specific name you must use to identify them is indicated by TOOL_NAME.
""".strip()

BUTTON_TOOL_INFO = """
<button_tool>
TOOL_NAME: "press_buttons"

The button tool allows you to submit one or more button presses to the emulator. It is useful for:
- Interacting with entities in the game.
- Opening the main menu.
- Rotating the player.
- Moving the player one or two tiles at a time.
- Transitioning from one map to another if you are at the edge of the current map or near/on a warp tile.

Give general guidance on which buttons to press in your thoughts, but do not provide specific button presses. The tool will determine the legal button presses and prompt you again to choose from them.
</button_tool>
""".strip()

NAVIGATION_TOOL_INFO = """
<navigation_tool>
TOOL_NAME: "navigation"

The navigation tool allows you to navigate to any revealed, accessible tile on the current map using an A* search algorithm. It is useful for:
- Moving the player around the current map. This should be your primary mode of movement, especially if you are trying to move more than a single tile at a time.
- Revealing unexplored territory on the current map.
- Navigating directly to warp tiles.
- Navigating to the boundaries of the current map

Note that the navigation tool cannot transition you from one map to another. It can bring you to the edge of the current map, but you will need to use the button tool on your next iteration to transition to the next map.

Give general guidance on where you want to go in your thoughts (e.g. to a given warp tile, to a given map boundary, to explore unexplored territory, towards a certain sprite, etc.), but do not provide specific coordinates. The navigation tool will determine the legal target coordinates and prompt you again to choose from them.
</navigation_tool>
""".strip()

CRITIQUE_TOOL_INFO = """
<critique_tool>
TOOL_NAME: "critique"

The critique tool is a powerful but expensive tool to get an external model to critique your performance and help get you unstuck. Use it if you are confused, or stuck in a loop, or failing to make progress towards your goals.  A good indication that you are stuck is if you are repeating the same actions over and over again. Do not use the critique tool if you are confident in your actions and are making progress towards your goals.
</critique_tool>
""".strip()
