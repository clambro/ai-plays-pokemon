GET_NAME_PROMPT = """
You are at the name entry screen.

{state}

Which name would you like to enter? Respond using the following keys:
- "thoughts": One or two sentences briefly considering what your current situation is and deciding on what an appropriate name would be and why. Make sure you actually say the name you would like to enter here in your thoughts.
- "name": The name you would like to enter, as stated in your thoughts. Whatever you enter will be assigned as the name, exactly as you enter it.

Naming rules:
- The name must be uppercase.
- The name must be at least one character long and at most eight characters long.
- The name can only contain the letters A-Z and spaces. Spaces count towards the eight character limit.
- The name cannot start or end with a space.
""".strip()
