GET_NAME_PROMPT = """
You are at the name entry screen.

{state}

Naming rules:
- The name must be uppercase.
- The name must be at least one character long and at most ten characters long.
  - The only exception to this is in the intro screen (iteration number less than 15) when you are entering the names for yourself and your rival. These names are at most seven characters long.
- The name can only contain the letters A-Z and spaces. Spaces count towards the character limit. Numbers are not allowed.
- The name cannot start or end with a space.
- Be creative. Don't use generic or default names. This is your chance to add some of your own personality to the game.

Respond using the following keys:
- "thoughts": One or two sentences briefly considering your situation and deciding on a good name. You must say the name you would like to enter here in your thoughts.
- "name": The name you would like to enter, as stated in your thoughts. Whatever you enter will be assigned as the name, exactly as you enter it.
""".strip()
