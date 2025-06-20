MAKE_DECISION_PROMPT = """
You are in a pokemon battle. The screenshot provided above is the current game screen. You must decide which button to press to proceed with the battle.

The (case-sensitive) available buttons are:
- a: The action button. Used to select the highlighted option or progress any on-screen text.
- b: The back button. Used to go back to the previous screen or decline a yes/no question.
- up: The up button. Used to move the cursor up one row.
- down: The down button. Used to move the cursor down one row.
- left: The left button. Used to move the cursor left one column.
- right: The right button. Used to move the cursor right one column.

{state}

Here is the game memory's representation of the onscreen text. The text you see below is exactly what the game is displaying on the screen, but the formatting may be somewhat messed up because it is not rendering images. Use it to help you understand the text on the screen, as well as the position of any cursors. This is a more reliable way to navigate menus than the screenshot.
<onscreen_text>
{text}
</onscreen_text>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your thoughts on the current game state and which button to press. What is the state of the battle? Where is the cursor? Consider all the information presented to you above; reflect on it, and then respond with your thoughts. Limit this to one or two sentences.
- button: The button to press. Must be one of the available buttons above.
""".strip()
