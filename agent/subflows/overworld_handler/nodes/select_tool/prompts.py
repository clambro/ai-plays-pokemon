SELECT_TOOL_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You must decide which of the available tools to use to proceed with the game.

{state}

You have the following tools at your disposal:
<tools>
{tools}
</tools>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your one sentence long thoughts on which tool that you would like to use given the information provided. Be sure to consider all the tools at your disposal. Your reasoning should be concise and based on the uses listed above for the tools. The tool that you select will continue this thought for you.
- tool: The tool to use. The only valid tools are the ones listed above in the <tools> section, and the specific name you must use to identify them is indicated by TOOL_NAME. Submitting a tool that is not listed above will result in an error.
""".strip()

BUTTON_TOOL_INFO = """
<press_buttons_tool>
TOOL_NAME: "press_buttons"

The button tool allows you to submit one or more button presses to the emulator. It is useful for:
- Interacting with entities in the game (speaking to NPCs, picking up items, reading signs, activating objects, etc.).
- Opening the main menu.
- Changing the direction that you are facing.
- Transitioning from one map to another if you are at the edge of the current map or on/near a warp tile.
- Rotating in place repeatedly in tall grass to find wild Pokemon. If you are doing this and failing to find wild Pokemon, you may not be standing in a place where wild Pokemon can be found. You should have at least two grass tiles adjacent to you to be confident that you are in a tall grass area.

The button tool can be used to move around the map, but it is not as reliable as the navigation tool. Do not use the button tool for general navigation if the navigation tool is available.

If you are standing next to an entity and wish to interact with it, just say so. Do not list the specific button presses that this requires. The button tool will handle this for you. The same goes for rotating in place to find wild Pokemon, just say that you want to rotate in place and the tool will handle the rest.

Give general guidance on which buttons to press in your thoughts, but do not provide specific button presses. The tool will determine the legal button presses and prompt you again to choose from them.
</press_buttons_tool>
""".strip()

NAVIGATION_TOOL_INFO = """
<navigation_tool>
TOOL_NAME: "navigation"

The navigation tool allows you to navigate to any revealed, accessible tile on the current map using an A* search algorithm. It is useful for:
- Moving the player around the current map. This should be your primary mode of movement, especially if you are trying to move more than a single tile at a time.
- Moving to a specific tile type (e.g. moving into tall grass or water to find wild Pokemon. You need access to Surf to move into water).
- Revealing unexplored territory on the current map.
- Navigating directly to warp tiles.
- Navigating to the boundaries of the current map

Note that the navigation tool cannot transition you from one map to another. It can bring you to the edge of the current map, but you will need to use the button tool on your next iteration to transition to the next map. Once you have switched maps, you can go back to using the navigation tool to move around the new map.

The navigation tool cannot be used to interact with entities, but it can be used to move to the tile next to them so that you can interact with them via the button tool on the next iteration.

The navigation tool intentionally tries to avoid random encounters with wild Pokemon for smoother navigation, and is thus not an efficient way to find wild Pokemon.

Do not attempt to navigate to the tile that you are currently standing on. This does nothing.

The navigation tool has access to a list of good exploration candidates in maps that are not fully explored. Asking the navigation tool to move to an exploration candidate is the fastest way to explore the map. You do not know where the exploration candidates are. Only the tool knows them, so don't provide any hallucinated exploration coordinates. Give a general description of where you want to go, specifically mention that you want to head to "an exploration candidate," and the tool will determine the best tile to move to.

Navigating directly to warp tiles that are marked in your overworld map as not yet visited is another effective way to explore new areas. Doing so will take you to a new map, usually a building, a cave, or a new floor of a building or cave.

Give general guidance on where you want to go in your thoughts (e.g. to a given warp tile, to a given map boundary, to explore unexplored territory, towards a certain sprite, etc.), but do not provide specific coordinates. The navigation tool will determine the legal target coordinates and prompt you again to choose from them.
</navigation_tool>
""".strip()

NAVIGATION_TOOL_BIKING_INFO = """
<warning>
You have lost access to the navigation tool because you are riding a bike. If you would like to use the navigation tool, you must first dismount your bike. If you are unable to dismount your bike because you are on Cycling Road, then you must use the button tool to move around the map.
</warning>
""".strip()

SWAP_FIRST_POKEMON_TOOL_INFO = """
<swap_first_pokemon_tool>
TOOL_NAME: "swap_first_pokemon"

The swap first Pokemon tool allows you to put a specific Pokemon in the first position in your party. This will make that Pokemon your lead Pokemon in battle (assuming it has not fainted).

This tool is useful for:
- Leading with an advantageous Pokemon before a major battle.
- Training a specific Pokemon by having it come out first in battle. If you want to train a specific Pokemon, use this tool to put it in the first position before starting your training session.
- Keeping your party members at roughly the same level as one-another by changing which Pokemon is the first to see action in battle.

Remember that Pokemon only gain experience when they are used in battle. Putting a Pokemon in the first position is a good way to guarantee that it will gain experience (assuming it has not fainted and is not at the level cap).

If you want to use this tool, be explicit in your thoughts about which Pokemon you would like to put in the first position. If you are happy with the order of your party, don't use this tool.
</swap_first_pokemon_tool>
""".strip()

USE_ITEM_TOOL_INFO = """
<use_item_tool>
TOOL_NAME: "use_item"

The use item tool allows you to use an item from your inventory in the overworld. It is useful for:
- Using helpful items like REPEL, ESCAPE ROPE, evolution stones, etc.
- Teaching a TM or HM to a Pokemon.
- Using a healing item like a POTION or a REVIVE. This is still allowed outside of battle in hard mode.

If you want to use this tool, be explicit in your thoughts about which item from your inventory you would like to use. If the item requires a target Pokemon (e.g. an evolution stone or a healing item), be explicit about which Pokemon you want to use it on.
</use_item_tool>
""".strip()

SOKOBAN_SOLVER_TOOL_INFO = """
<sokoban_solver_tool>
TOOL_NAME: "sokoban_solver"

The Sokoban solver tool will automatically solve the onscreen Sokoban puzzle for you, or inform you if the puzzle is not currently solvable (likely meaning that you need to explore more).
</sokoban_solver_tool>
""".strip()

CRITIQUE_TOOL_INFO = """
<critique_tool>
TOOL_NAME: "critique"

The critique tool is a powerful but expensive tool to get an external model to critique your performance and help get you unstuck. Use it if you are confused, stuck in a loop, or failing to make progress towards your goals.  A good indication that you are stuck is if you are repeating the same actions over and over again. Do not use the critique tool if you are confident in your actions and are making progress towards your goals.
</critique_tool>
""".strip()
