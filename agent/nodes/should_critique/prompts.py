SHOULD_CRITIQUE_PROMPT = """
Take a step back from playing the game for a moment. It is time to reflect on your performance so far. You have access to a powerful (but expensive) tool to critique your performance and help get you unstuck. Your job is to determine whether or not you should use this tool.

{player_info}

{raw_memory}

{goals}

Look carefully at the game information displayed above, especially at your memories of past events, with a bias towards the most recent events. Are you stuck in a loop? Are you walking back and forth? Are you failing to make progress towards your goals? If so, this is your chance to use the critique tool to help you get unstuck. If you seem to be moving forward and making progress towards your goals, you should not use the critique tool.

Think through the information above carefully and then give a boolean answer as to whether or not you should use the critique tool. Being stuck will be obvious, so when in doubt, you should not use the critique tool.
""".strip()
