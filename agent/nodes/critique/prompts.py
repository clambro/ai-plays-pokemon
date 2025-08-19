CRITIQUE_PROMPT = """
Stop. Take a step back from playing the game for a moment. You have been imbued with significantly more intelligence and memory than you had before. This is your chance to review your past actions, as well as the current state of the game and provide a critique of your performance so far, as well as a plan for the next steps you should take.

{state}

Here is the game memory's representation of the onscreen text (if any is present). The formatting of the text may be somewhat messed up because it is not rendering images. Use it to help you understand any text on the screen, as well as the position of any cursors. If you see multiple cursors "▷" and "▶", you are probably in a nested menu. The active cursor is always "▶".
<onscreen_text>
{onscreen_text}
</onscreen_text>
If you see garbled, nonsensical text in the onscreen text, it is because the game is rendering an image, which the memory stores as text. If this is the case, use the screenshot to help you better understand what is going on.

Critique your performance so far. Are you stuck? Why are you stuck? Where did you go wrong? What should you do to make meaningful progress towards your goals? Keep your critique to one paragraph max, and focus on the things that you are most certain about. Do not include unfounded speculation in your critique.
""".strip()
