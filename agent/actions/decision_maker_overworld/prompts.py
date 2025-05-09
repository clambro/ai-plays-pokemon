DECISION_MAKER_OVERWORLD_PROMPT = """
You are navigating the overworld. The screenshot provided above is the current game screen. You must decide which button to press to proceed with the game.

The (case-sensitive) available buttons are:
- a: The action button. Used to interact with objects in the game.
- start: Used to open the main menu.
- up: Used to move the character upwards.
- down: Used to move the character downwards.
- left: Used to move the character left.
- right: Used to move the character right.

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
    4. Consider the map information provided to you. Where are you, and where do you want to go? Are there sprites or warp tiles that you haven't checked out yet? Is there something blocking your path?
    5. Consider the screenshot. What is currently on the screen? How does it help you contextualize your situation?
    6. Synthesize the above information, and decide which button to press.
- button: The button to press. Must be one of the available buttons above.
""".strip()
