CRITIQUE_PROMPT = """
Take a step back from playing the game for a moment. You have signaled that you are feeling stuck. You have been imbued with significantly more intelligence and memory than you had before. This is your chance to review your past actions, as well as the current state of the game and provide a critique of your performance so far, as well as a plan for the next steps you should take.

{player_info}

{current_map}

{goals}

{raw_memory}

Give a thorough critique of your performance so far. Why are you stuck? Where did you go wrong? What should you do to make meaningful progress towards your goals?
""".strip()
