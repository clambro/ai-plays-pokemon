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

{player_info}

The following is an ASCII representation of the current map, highlighting your current location. Note that the screenshot above is only a subset of the current map, centered on your current location.
{current_map}

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your written thoughts on the current game state and which button to press. Use the following thought process, and be thorough in your commentary:
    1. Consider your goals. What are you trying to accomplish?
    2. Consider the information provided in the raw memory. What has happened lately?
    3. Consider the player information provided to you. What is your current situation?
    4. Consider the map information provided to you, as well as the accompanying screenshot. Where are you, and where do you want to go?
    5. Synthesize the above information, and decide which button to press.
- button: The button to press. Must be one of the available buttons above.
""".strip()
