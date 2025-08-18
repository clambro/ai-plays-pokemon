CHOOSE_ARGS_PROMPT = """
You are in a Pokemon battle. The screenshot provided above is the current game screen. You must decide which action to take based on the available options.

{state}

Here is the game memory's representation of the onscreen text. The text you see below is exactly what the game is displaying on the screen, but the formatting may be somewhat messed up because it is not rendering images. Use it to help you understand the text on the screen, as well as the position of any cursors. If you see multiple cursors "▷" and "▶", you are probably in a nested menu. The active cursor is always "▶". This is a more reliable way to navigate menus than the screenshot, but keep the screenshot in mind as well.
<onscreen_text>
{text}
</onscreen_text>
If you see garbled, nonsensical text in the onscreen text, it is because the game is rendering an image, which the memory stores as text. If this is the case, use the screenshot to help you better understand what is going on.

The available actions are:
<actions>
{actions}
</actions>
Note that all of the above actions will use up your turn, and your opponent will have the opportunity to attack you. This means that if you switch Pokemon, your opponent will get a free attack against the Pokemon that you switch into.

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your thoughts on the current game state and which action to take. What is the state of the battle? If present, where is the cursor? Consider all the information presented to you above; reflect on it, and then respond with your thoughts. Limit this to one or two sentences.
- index: The index of the action to take (the number in the square brackets).
""".strip()
