UPDATE_GOALS_PROMPT = """
You have just taken an action and added new information to your memory. If you you feel that recent events warrant removing/completing past goals, or adding new goals, this is your chance to do so.

{agent_memory}

{player_info}

{goals}

To add or remove goals, respond according to the schema given below. The meaning of the fields is as follows:
- "remove" is an array of goal indices to remove. You should only remove goals that you have already completed, or that you no longer want to pursue. Goals to be removed are referred to by the index given above. The remove array should be empty if there are no goals to remove.
- "append" is an array of new goals to add, in string format. Do not include an index in the append array, just the goal text. These should be goals that you want to pursue, and which are not already in your list. The append array should be empty if there are no new goals to add.

If you want to edit the text of an existing goal from the list (e.g. because you acquired new information about it), you can do so by removing the goal in the remove array, and then adding back the edited goal in the append array.

Remember that a good goal must be SMART:
- Specific: The goal must be clearly defined and not vague.
  - Bad: "Level up my Pokemon"
  - Good: "Level up my [pokemon] to level [level]"
- Measurable: The goal must have clear criteria for success.
  - Bad: "Complete Pewter City"
  - Good: "Defeat Brock in the Pewter City Gym and collect the Boulder Badge"
- Achievable: The goal must be doable within the confines of the game.
  - Bad: "Get my whole team to level 100" (not possible before becoming the Champion due to the level cap)
  - Good: "Catch a [pokemon] in [location]" (assuming that you have seen that pokemon at that location)
- Relevant: The goal must be relevant to your ultimate goal of collecting all eight badges and becoming the Champion.
  - Bad: "Catch 100 Magikarp" (silly and pointless)
  - Good: "Get my team up to the current level cap of level [level] before challenging [major opponent]"
- Time-bound: The least-relevant of the SMART criteria for your purposes, but try to ensure that your goals have clear temporal boundaries when relevant.
  - Suboptimal: "Catch a [pokemon] in [location]"
  - Good: "Catch a [pokemon] in [location] and add it to my team before challenging [major opponent]"

New goals should be based on your experience in the game as recorded in your memory or the player info above, not based on your prior knowledge of Pokemon, which is prone to error. Similarly, do not assume that you have accomplished a goal until you are certain that you have done so based on the information in your memory and the player info above.

Read the instructions above carefully and update your goals. Remember that doing nothing here is a valid response if you are satisfied with your current goals. Only update your goals if you feel that recent events warrant it. You must have at least one goal at any given time, and try to have no more than five active at once. The upper limit is not strict, but try to keep your goals manageable.
""".strip()
