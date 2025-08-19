CRITIQUE_PROMPT = """
Stop. Take a step back from playing the game for a moment. You have signaled that you are feeling stuck. You have been imbued with significantly more intelligence and memory than you had before. This is your chance to review your past actions, as well as the current state of the game and provide a critique of your performance so far, as well as a plan for the next steps you should take.

{state}

Here is the game memory's representation of the onscreen text. If this section is empty then no text is present. The formatting of the text may be somewhat messed up because it is not rendering images. Use it to help you understand any text on the screen, as well as the position of any cursors. If you see multiple cursors "▷" and "▶", you are probably in a nested menu. The active cursor is always "▶".
<onscreen_text>
{onscreen_text}
</onscreen_text>
If you see garbled, nonsensical text in the onscreen text, it is because the game is rendering an image, which the memory stores as text. If this is the case, use the screenshot to help you better understand what is going on.

Common sources of error include (but are not limited to):
- Misinterpreting the screenshot. Your vision skills have improved in this critique prompt, but they are still fallible.
- Incorrectly deciding that the screenshot or your own memory is more reliable than the game data.
- Making false assumptions and failing to correct them. This includes in past critiques. Do not be afraid to correct your own past mistakes, even if those mistakes came from the critic model.
- Not taking advantage of your available tools to help you with more complex tasks.
- Misinterpreting the position of the cursor and trying to select the wrong menu option.
- Not exploring the game world enough. If you are in the overworld, ask yourself if there is any unexplored territory or unvisited warp tiles that you have not yet visited.
- Getting stuck in a menu loop. You can usually bail out of a menu loop by repeatedly pressing the "b" button.
- Thinking that all your Pokemon have fainted and that you are unable to progress. The game will not allow this. If all your Pokemon have fainted, you will automatically be sent back to the last Pokemon Center you visited, which will break any loop you are in. That means that if you are in a loop, you are *not* out of usable Pokemon.
- Thinking that you are unable to act or move. You almost certainly can. There are no cutscenes or invisible walls or traps that lock the player indefinitely.
- Doing the same thing over and over again and expecting different results. If you are stuck in a loop, try doing something completely different. Anything to break out of the cycle.

Pay extra attention to the raw memory, especially the most recent iterations, as those are the memories that triggered this decision to critique. High level critiques are useful too, but the main reason you are here is to get unstuck.

Critique your performance so far. Why are you stuck? Where did you go wrong? What should you do to break your current loop and make meaningful progress towards your goals? Keep your critique to one paragraph max, and focus on the things that you are most certain about. Do not include unfounded speculation in your critique.
""".strip()
