CRITIQUE_PROMPT = """
Take a step back from playing the game for a moment. You have signaled that you are feeling stuck. You have been imbued with significantly more intelligence and memory than you had before. This is your chance to review your past actions, as well as the current state of the game and provide a critique of your performance so far, as well as a plan for the next steps you should take.

{player_info}

{current_map}

{goals}

{raw_memory}

Common sources of error include (but are not limited to):
- Misinterpreting the screenshot information
- Incorrectly deciding that the screenshot is more reliable than the 100% accurate game memory data
- Making false assumptions and failing to correct them
- Not exploring the game world enough, especially the current map. If this is the case, you should point out exactly where you should be exploring. Which direction should you be going in?

Give a thorough critique of your performance so far. Why are you stuck? Where did you go wrong? What should you do to make meaningful progress towards your goals?
""".strip()
