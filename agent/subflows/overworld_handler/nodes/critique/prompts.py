CRITIQUE_PROMPT = """
Take a step back from playing the game for a moment. You have signaled that you are feeling stuck. You have been imbued with significantly more intelligence and memory than you had before. This is your chance to review your past actions, as well as the current state of the game and provide a critique of your performance so far, as well as a plan for the next steps you should take.

{state}

Common sources of error include (but are not limited to):
- Misinterpreting the screenshot information
- Misinterpreting the map information and trying to walk through walls
- Misunderstanding warp tiles and trying to walk through them in the wrong direction
- Incorrectly deciding that the screenshot or your own memory is more reliable than the infallible game data
- Making false assumptions and failing to correct them
- Not taking advantage of your available tools to help you with more complex tasks
- Not exploring the game world enough, especially the current map. If this is the case, you should point out exactly where you should be exploring. Which direction should you be going in?

Critique your performance so far. Why are you stuck? Where did you go wrong? What should you do to make meaningful progress towards your goals? Keep your critique to a couple paragraphs max, and focus on the things that you are most certain about. Do not include unfounded speculation in your critique.
""".strip()
