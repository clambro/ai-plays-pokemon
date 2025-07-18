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
I need to swap Zippy the Pikachu for Shelly the Squirtle.
</thought>
<party_info>
<pokemon_0>
Name: Zippy
Species: Pikachu
</pokemon_0>
<pokemon_1>
Name: Shelly
Species: Squirtle
</pokemon_1>
<pokemon_2>
Name: Bubba
Species: Rattata
</pokemon_2>
</party_info>
</example_input>

<example_output>
{
    "thoughts": "Zippy the Pikachu is currently in position 0, and I want Shelly the Squirtle to be the first Pokemon in my party. It is currently in position 1, so I will return 1.",
    "index": 1
}
</example_output>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your very brief thoughts on which Pokemon to swap the first Pokemon in your party with based on the thought and party information provided to you in this prompt.
- index: The index of the Pokemon to swap the first Pokemon in your party with. This must be one of the indices listed above, but not zero since that Pokemon is already the first Pokemon in your party.
""".strip()
