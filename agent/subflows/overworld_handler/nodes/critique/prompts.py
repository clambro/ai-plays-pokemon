CRITIQUE_PROMPT = """
Take a step back from playing the game for a moment. You have signaled that you are feeling stuck. You have been imbued with significantly more intelligence and memory than you had before. This is your chance to review your past actions, as well as the current state of the game and provide a critique of your performance so far, as well as a plan for the next steps you should take.

{state}

Common sources of error include (but are not limited to):
- Misinterpreting the screenshot. Your vision skills have improved in this critique prompt, but they are still fallible.
- Misinterpreting the map information. If this is the case, use your increased intelligence to explain the misinterpretation and correct it.
- Misinterpreting sprite labels or warp tile descriptions. Rely on the game's memory for this information, not your own assumptions.
- Incorrectly deciding that the screenshot or your own memory is more reliable than the game data.
- Making false assumptions and failing to correct them. This includes in past critiques. Do not be afraid to correct your own past mistakes, even if those mistakes came from the critic model.
- Not taking advantage of your available tools to help you with more complex tasks
- Not exploring the game world enough, especially the current map. If this is the case, you should point out exactly where you should be exploring. If you can't seem to find a valid path in one direction, is there unexplored terrain in another direction that you can try? Are there warp tiles that you can use to get to a new map?
- Thinking that you are unable to act or move. You almost certainly can. There are no cutscenes or invisible walls or traps that lock the player indefinitely. If you are in the overworld, you can always move.
- Doing the same thing over and over again and expecting different results. If you are walking in circles, try doing something completely different. Go to a new area. Anything to break out of the cycle.

Critique your performance so far. Why are you stuck? Where did you go wrong? What should you do to make meaningful progress towards your goals? Keep your critique to one paragraph max, and focus on the things that you are most certain about. Do not include unfounded speculation in your critique.
""".strip()
