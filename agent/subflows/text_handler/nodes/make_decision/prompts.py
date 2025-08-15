DECISION_MAKER_TEXT_PROMPT = """
There is text on the screen. The screenshot provided above is the current game screen. You must decide which button(s) to press to proceed with the game.

{state}

Here is the game memory's representation of the onscreen text. The text you see below is exactly what the game is displaying on the screen, but the formatting may be somewhat messed up because it is not rendering images. Use it to help you understand the text on the screen, as well as the position of any cursors. If you see multiple cursors "▷" and "▶", you are probably in a nested menu. The active cursor is always "▶". This is a more reliable way to navigate menus than the screenshot, but keep the screenshot in mind as well.
<onscreen_text>
{text}
</onscreen_text>
If you see garbled, nonsensical text in the onscreen text, it is because the game is rendering an image, which the memory stores as text. If this is the case, use the screenshot to help you better understand what is going on.

The (case-sensitive) available buttons are:
- a: The action button. Used to select a menu option or to continue the text.
- b: The back button. Used to go back to the previous screen, close a menu, or decline a yes/no question.
- start: Only purpose is to sort the bag in the bag screen.
- up: Used to navigate the cursor up.
- down: Used to navigate the cursor down.
- left: Used to navigate the cursor left.
- right: Used to navigate the cursor right.

Remember: If you feel stuck or lost in a nested menu and you aren't sure what to do, you can usually press the "b" button to back out of it. If you find that you are stuck in a loop, pressing "b" three or four times in sequence will likely break you out of it.

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your thoughts on the current game state and which button(s) to press. Keep this to one or two sentences. It is important that you note any text that you are reading in your thoughts, otherwise you will lose access to it in subsequent turns.
- buttons: The button(s) to press in sequence. Must be one or more of the available buttons above. You should generally only press one button at a time, but you may press multiple buttons in sequence to, say, move the cursor multiple times in a menu, or to move and then select an item in a single response, or to totally bail out of a nested menu.
""".strip()
