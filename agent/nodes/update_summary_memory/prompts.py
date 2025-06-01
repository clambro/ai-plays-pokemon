UPDATE_SUMMARY_MEMORY_PROMPT = """
You have taken some actions and have added new information to your raw memory. This is your chance to update your summary memory. Your raw memory is limited to the last {raw_memory_max_size} actions. This is your chance to consolidate and retain any information from your raw memory that you feel is important.

{state}

To update your summary memory, respond according to the schema given below. The meaning of the fields is as follows:
- "description" is the exact string that you want to add to your summary memory.
- "importance" is an integer between 1 and 5 representing how important you think this information is. The scale is as follows:
  - 5: Critical milestones that moved you towards your ultimate goal (e.g. defeating a gym leader, finding a key item, etc.)
  - 4: Important moments that are good to remember (e.g. catching a new Pokemon, encountering a notable character, entering a new town for the first time, getting an HM, etc.)
  - 3: Significant events that occurred in the game (e.g. evolving a Pokemon, seeing a new species of Pokemon for the first time, learning a new move, etc.)
  - 2: Normal events that occurred in the game (e.g. defeating a trainer, finding an item, level ups, etc.)
  - 1: Trivial information (e.g. walking from one place to another, reading flavour text, wild Pokemon battles, etc.)

IMPORTANT: You will not be able to edit your summary memories once you have submitted your response, so make sure that you are only summarizing information that:
1. You are not mistaken about.
2. Is not already in your summary memory. Do not add duplicates to your summary memory.
3. Is complete (e.g. do not summarize an ongoing process, only summarize something that is finished). A good rule of thumb is to not summarize anything from the most recent 20 iterations. The current iteration is {iteration}.

Remember that your summary memory is limited in size, and that individual entries cannot be edited once they are added. Be judicious with your entries. You should submit no more than one summary memory for this iteration. Submitting an empty list is fine if you feel that there is no new information to add.
""".strip()
