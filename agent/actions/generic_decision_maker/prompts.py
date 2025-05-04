GENERIC_DECISION_MAKER_PROMPT = """
Based on the screenshot provided, decide which button to press. The (case-sensitive) available buttons are:
- a: The action button. Used to interact with objects in the game or select options.
- b: The back button. Used to go back to the previous screen or decline a yes/no question.
- start: The start button. Used to open the menu in the overworld, or to sort the bag in the bag screen.
- up: The up button. Used to navigate menus or move the character upwards.
- down: The down button. Used to navigate menus or move the character downwards.
- left: The left button. Used to navigate menus or move the character left.
- right: The right button. Used to navigate menus or move the character right.

{raw_memory}

You have been provided with the current game screen. Respond in the format given below. The relevant keys are:
- thoughts: Your thoughts on the current game state and which button to press.
- button: The button to press. Must be one of the available buttons above.
""".strip()
