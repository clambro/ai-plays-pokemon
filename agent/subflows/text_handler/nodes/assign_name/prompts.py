GET_NAME_PROMPT = """
You are at the name entry screen. Use the information below to figure out what it is that you are being asked to assign a name to. It is almost certainly a nickname for a Pokemon. The only exception is if the raw memory iteration number is less than 15, in which case you are either entering the names for yourself and your rival.

{raw_memory}

{player_info}

Naming rules:
- The name must be uppercase.
- The name must be at least one character long and at most ten characters long.
  - The only exception to this is in the intro screen (iteration number less than 15) when you are entering the names for yourself and your rival. These names are at most seven characters long.
- The name can only contain the letters A-Z and spaces. Spaces count towards the character limit. Numbers are not allowed.
- The name cannot start or end with a space.
- Be creative. Names must be unique. Don't use generic or default names. This is your chance to add some of your own personality to the game.

Respond using the following keys:
- "thoughts": One or two sentences briefly considering your situation and deciding on a good name. You must say the name you would like to enter here in your thoughts.
- "name": The name you would like to enter, as stated in your thoughts. Whatever you enter will be assigned as the name, exactly as you enter it.
""".strip()
