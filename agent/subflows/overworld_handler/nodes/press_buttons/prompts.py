PRESS_BUTTONS_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You have decided to submit one or more button presses to the emulator.

{state}

The following (case-sensitive) buttons are available to you:
- a: The action button. Used to interact with objects in the game. The object you interact with will be the tile directly adjacent to you, in the direction that you are facing. The only exception to this is if you are interacting with a clerk at a mart or a nurse at a Pokemon Center. In these cases, you will use the action button on the counter in front of the clerk or nurse.
- start: Used to open the main menu.
- up: Used to move the player upwards.
- down: Used to move the player downwards.
- left: Used to move the player left.
- right: Used to move the player right.

Your most recent raw memory is repeated below for reference. The "thoughts" in your response will be appended verbatim to the end of this memory, so there is no need to duplicate information.
<last_memory>
{last_memory}
</last_memory>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your one sentence long thoughts on which buttons to press given the information provided.
- buttons: The button(s) to press. This can either be a single button, or a list of buttons to be pressed in sequence. You should generally prefer to press a single button at a time, but you can use a combination of buttons to, say, rotate the player and then interact with an object.
""".strip()
