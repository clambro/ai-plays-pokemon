DECISION_MAKER_OVERWORLD_PROMPT = """
You are in the overworld. The screenshot provided above is the current game screen. You must decide which button to press to proceed with the game.

The (case-sensitive) available buttons are:
- a: The action button. Used to interact with objects in the game or select a menu option.
- b: The back button. Used to go back to the previous screen or decline a yes/no question.
- start: The start button. Used to open the main menu in the overworld, or to sort the bag in the bag screen.
- up: The up button. Used to navigate menus or move the character upwards.
- down: The down button. Used to navigate menus or move the character downwards.
- left: The left button. Used to navigate menus or move the character left.
- right: The right button. Used to navigate menus or move the character right.

{raw_memory}

{goals}

The following is an ASCII representation of the current map, highlighting your current location. Note that the screenshot above is only a subset of the current map, centered on your current location.
{current_map}

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your thoughts on the current game state and which button to press. These must be detailed and descriptive, accurately reflecting the information available to you and conveying your thought process.
- button: The button to press. Must be one of the available buttons above.
""".strip()
