DECISION_MAKER_BATTLE_PROMPT = """
You are in a pokemon battle. The screenshot provided above is the current game screen. You must decide which button to press to proceed with the battle.

The (case-sensitive) available buttons are:
- a: The action button. Used to select the highlighted option or progress any on-screen text.
- b: The back button. Used to go back to the previous screen or decline a yes/no question.
- up: The up button. Used to move the cursor up one row.
- down: The down button. Used to move the cursor down one row.
- left: The left button. Used to move the cursor left one column.
- right: The right button. Used to move the cursor right one column.

{raw_memory}

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your thoughts on the current game state and which button to press. These must be detailed and descriptive, accurately reflecting the information available to you and conveying your thought process.
- button: The button to press. Must be one of the available buttons above.
""".strip()
