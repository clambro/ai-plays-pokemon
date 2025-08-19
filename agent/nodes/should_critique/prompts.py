SHOULD_CRITIQUE_PROMPT = """
Stop. Take a step back from the game. In this prompt it is your job to determine if you are stuck in a loop by looking at your raw memory and current goals.

{raw_memory}

{goals}

If you feel that you are stuck in a loop, a smarter model will step in to critique your performance and help get you unstuck. Here are some (non-exhaustive) examples of what being stuck in a loop might look like:
- You are navigating back and forth between the same two or three tiles
- You are in a menu and keep selecting the same option or cycle of options
- Your latest memories contain complaints about being unable to move/act/progress
- Your last ten or so memories are all nearly identical
- Your actions seem pointless and unrelated to your goals

Successfully navigating to different exploration candidates is *not* a sign of being stuck in a loop, as long as the target coordinates are all different and it feels like you are making progress exploring the area.

The critic model is expensive to run. Only invoke it if you are sure that you are stuck in a loop.

The keys for the response are as follows:
- "thoughts": 1-2 short sentences reflecting on the raw memory and goals to determine if you are stuck in a loop.
- "is_stuck": A boolean value determining if you are stuck in a loop.
"""
