PRESS_BUTTONS_PROMPT = """
You are navigating the overworld. You are standing still. There is no onscreen text, and all onscreen animations have concluded. The screenshot provided above is the current game screen, and it is awaiting your input. You have decided to submit one or more button presses to the emulator.

{state}

The following (case-sensitive) buttons are available to you:
- a: The action button. Used to interact with objects in the game. Make sure you are facing the direction of the object that you wish to interact with before pressing the action button.
- start: Used to open the main menu.
- up: Used to move the player upwards.
- down: Used to move the player downwards.
- left: Used to move the player left.
- right: Used to move the player right.

Tips:
- You can interact with warp tiles by walking on or through them, depending on the instructions provided in the warp tile's description above.
- You can interact with sprites or signs using the action button, but you must be facing the entity you wish to interact with before doing so. If the sprite's position is (r, c) and you are at (r, c + 1), then you must face left to interact with it. If you are at (r - 1, c), then you must face down to interact with it. If you are at (r, c - 1), then you must face right to interact with it. If you are at (r + 1, c), then you must face up to interact with it.
- With nearly all sprites, you must be directly adjacent to them before using the action button. The only exceptions are if you are interacting with a clerk at a mart, a nurse at a Pokemon Center, or a guard at a gate. In these cases, you interact with the counter in front of the sprite, meaning that you must be two tiles away from the sprite (horizontally or vertically depending on the counter, but not diagonally).
- If you have been given instructions to rotate in place repeatedly in tall grass to find wild Pokemon and you are facing up or down, return a series of left and right button presses like so: [left, right, left, right, left, right]. If you are facing left or right, return a series of up and down button presses like so: [up, down, up, down, up, down].

Your most recent raw memory is repeated below for reference. The "thoughts" in your response will be appended verbatim to the end of this memory, so there is no need to duplicate information.
<last_memory>
{last_memory}
</last_memory>
If you see specific button presses in the <last_memory> section, do not treat them as mandatory. You have more information available to you in this prompt than you did when the above memory was generated, so you are allowed to overrule it if the request does not make sense (e.g. if it is asking you to face right to interact with a sprite that is to your left). Determine what the memory is trying to tell you and choose the best button(s) from the list of available buttons above.

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your one sentence long thoughts on which buttons to press given the information provided. These thoughts will be appended verbatim to the end of the <last_memory> in your raw memory, so try to continue the thought process from there.
- buttons: The button(s) to press. This can either be a single button, or a list of buttons to be pressed in sequence. You should generally prefer to press a single button at a time, but you can use a combination of buttons to, say, rotate the player and then interact with an object.
""".strip()
