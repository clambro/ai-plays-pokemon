PRESS_BUTTONS_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You have decided to submit one or more button presses to the emulator.

{state}

The following (case-sensitive) buttons are available to you:
- a: The action button. Used to interact with objects in the game. The object you interact with will be the tile directly adjacent to you, in the direction that you are facing.
- start: Used to open the main menu.
- up: Used to move the player upwards.
- down: Used to move the player downwards.
- left: Used to move the player left.
- right: Used to move the player right.

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your written thoughts on the current game state and which buttons to press in response. Pay particular attention to the most recent raw memory, as that will tell you why you chose to use the button pressing tool.
- buttons: The button(s) to press. This can either be a single button, or a list of buttons to be pressed in sequence. You should generally prefer to press a single button at a time, but you can use a combination of buttons to, say, rotate the player and then interact with an object.
""".strip()
