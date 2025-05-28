DECISION_MAKER_TEXT_PROMPT = """
There is text on the screen. The screenshot provided above is the current game screen. You must decide which button to press to proceed with the game.

The (case-sensitive) available buttons are:
- a: The action button. Used to select a menu option or to continue the text.
- b: The back button. Used to go back to the previous screen or decline a yes/no question.
- start: Only purpose is to sort the bag in the bag screen.
- up: Used to navigate the cursor up.
- down: Used to navigate the cursor down.
- left: Used to navigate the cursor left.
- right: Used to navigate the cursor right.

{agent_memory}

{goals}

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your thoughts on the current game state and which button to press. These must be detailed and descriptive, accurately reflecting the information available to you and conveying your thought process. It is important that you note any text that you are reading in your thoughts, otherwise you will lose access to it in subsequent turns.
- button: The button to press. Must be one of the available buttons above.
""".strip()
