UPDATE_GOALS_PROMPT = """
You have just taken an action and added new information to your memory. If you feel that recent events warrant removing/completing past goals, or adding new goals, this is your chance to do so.

{state}

To add or remove goals, respond according to the schema given below. The meaning of the fields is as follows:
- "remove" is an array of goal indices to remove. You should only remove goals that you have already completed, or that you no longer want to pursue. Goals to be removed are referred to by the index given above. The remove array should be empty if there are no goals to remove.
- "append" is an array of new goals to add. Do not include an index in the append array, just the goal text and the priority. These should be goals that you want to pursue, and which are not already in your list. The append array should be empty if there are no new goals to add.

There are three priority levels for goals:
- Primary: These represent major milestones like gym battles or other key objectives required to progress the game. You must have exactly one primary goal at a time, and you should update it sparingly.
- Secondary: These directly support the primary goal. Examples include finding a specific item required for the primary goal, or navigating to a specific map to get to the primary goal. You can have up to three secondary goals at once. There is no minimum requirement. Achieving a secondary goal should be a meaningful step towards achieving the primary goal. If you change your primary goal, you must remove (or at least update) all secondary goals that are no longer relevant. The secondary goals must support the current primary goal.
- Tertiary: These are not related to the primary goal, but could still be important to pursue. Examples include catching Pokemon, training your Pokemon, healing your Pokemon, buying items, exploring an area, etc. You can have up to three tertiary goals at once. There is no minimum requirement. You can update/add/remove tertiary goals more frequently than primary or secondary goals, but generally you should do so only if they have been completed or are no longer relevant.

If you want to edit the text of an existing goal from the list (e.g. because you acquired new information about it), you can do so by removing the goal in the remove array, and then adding back the edited goal in the append array.

Remember that a good goal must be SMART:
- Specific: The goal must be clearly defined and not vague.
  - Bad: "Level up my Pokemon"
  - Good: "Level up my [pokemon] to level [level]"
- Measurable: The goal must have clear criteria for success.
  - Bad: "Complete Pewter City"
  - Good: "Defeat Brock in the Pewter City Gym and collect the BOULDERBADGE"
- Achievable: The goal must be possible within the confines of the game.
  - Bad: "Get my whole team to level 100" (not possible before becoming the Champion due to the level cap)
  - Good: "Catch a [pokemon] in [location]" (assuming that you have seen that Pokemon at that location)
- Relevant: The goal must be relevant to your ultimate goal of collecting all eight badges and becoming the Champion. Completing the Pokedex is not relevant to this goal, except insofar as you need to catch Pokemon to build your team.
  - Bad: "Catch five Magikarp" (silly and pointless)
  - Good: "Catch a [pokemon] in [location] and add it to my team to help me defeat [major opponent]"
- Time-bound: The least-relevant of the SMART criteria for your purposes, but try to ensure that your goals have clear temporal boundaries when relevant.
  - Suboptimal: "Heal my Pokemon at the [location] Pokemon Center"
  - Good: "Heal my Pokemon at the [location] Pokemon Center before heading to [next location]"

Your goals should also be distinct from one another. You should not have multiple goals that are essentially the same thing, even if they are of different priorities. If you have multiple goals that are essentially the same thing, you should either combine them into a single goal, or remove the less important one(s).

New goals should be based on your experience in the game as recorded in your memory or the player info above, not based on your prior knowledge of Pokemon, which is prone to error. Similarly, do not assume that you have accomplished a goal until you are certain that you have done so based on the information in your memory and the player info above.

Read the instructions above carefully and update your goals. Remember that doing nothing here is a valid response if you are satisfied with your current goals. Only update your goals if you feel that recent events warrant it. You must have at least one goal at any given time. Try to have no more than five active at once.
""".strip()
