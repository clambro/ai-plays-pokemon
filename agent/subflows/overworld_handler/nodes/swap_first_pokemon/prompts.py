"""LLM prompts for swap first Pokémon in the overworld subflow."""

SWAP_FIRST_POKEMON_PROMPT = """
You have decided to swap the first Pokemon in your party with another Pokemon. Below is the thought in which you made this decision:
<thought>
{thought}
</thought>

In this prompt, you must interpret the thought above and determine which Pokemon to swap the first Pokemon in your party with. Your current party in their current order is listed below:
{party_info}

Note the base zero indexing of the party Pokemon above. Those are the indices you must use in your response.

<example_input>
<thought>
I need to swap ZIPPY the PIKACHU for SHELLY the SQUIRTLE.
</thought>
<party_info>
<pokemon_0>
Name: ZIPPY
Species: PIKACHU
</pokemon_0>
<pokemon_1>
Name: SHELLY
Species: SQUIRTLE
</pokemon_1>
<pokemon_2>
Name: BUBBA
Species: RATTATA
</pokemon_2>
</party_info>
</example_input>

<example_output>
{{
    "index": 1
}}
</example_output>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- index: The index of the Pokemon to swap the first Pokemon in your party with. This must be one of the indices listed above. If the Pokemon you want to swap with is already the first Pokemon in your party, you should return 0 to do nothing.
""".strip()
