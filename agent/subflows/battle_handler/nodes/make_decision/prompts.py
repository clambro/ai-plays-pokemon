MAKE_DECISION_PROMPT = """
You are in a Pokemon battle. The screenshot provided above is the current game screen. You must decide which button(s) to press to proceed with the battle.

{state}

Here is the game memory's representation of the onscreen text. The text you see below is exactly what the game is displaying on the screen, but the formatting may be somewhat messed up because it is not rendering images. Use it to help you understand the text on the screen, as well as the position of any cursors. If you see multiple cursors "▷" and "▶", you are probably in a nested menu. The active cursor is always "▶". This is a more reliable way to navigate menus than the screenshot, but keep the screenshot in mind as well.
<onscreen_text>
{text}
</onscreen_text>
If you see garbled, nonsensical text in the onscreen text, it is because the game is rendering an image, which the memory stores as text. If this is the case, use the screenshot to help you better understand what is going on.

Note: If you keep seeing the text "There's no will to fight" over and over again, it means that you are trying to switch into a fainted Pokemon. You cannot do this. You must switch to a Pokemon that has not fainted. If you are seeing this text, at least one of your Pokemon is still able to fight. Use the directional buttons to pick a different Pokemon to switch to.

The (case-sensitive) available buttons are:
- a: The action button. Used to select the highlighted option or progress any on-screen text.
- b: The back button. Used to go back to the previous screen or decline a yes/no question.
- up: The up button. Used to move the cursor up one row.
- down: The down button. Used to move the cursor down one row.
- left: The left button. Used to move the cursor left one column.
- right: The right button. Used to move the cursor right one column.

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your thoughts on the current game state and which button to press. What is the state of the battle? If present, where is the cursor? Consider all the information presented to you above; reflect on it, and then respond with your thoughts. Limit this to one or two sentences.
- buttons: The button(s) to press in sequence. Must be one or more of the available buttons above. You should generally only press one button at a time, but you may press multiple buttons in sequence to, say, move the cursor multiple times in a menu.
""".strip()
