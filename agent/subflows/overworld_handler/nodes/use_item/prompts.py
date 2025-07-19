USE_ITEM_PROMPT = """
You have decided to use an item from your inventory. Below is the thought in which you made this decision:
<thought>
{thought}
</thought>

In this prompt, you must interpret the thought above and determine which item to use. Your current inventory is listed below:
<inventory>
{inventory}
</inventory>

<example_input>
<thought>
I need to use a Potion on my Pikachu.
</thought>
<inventory>
[0] POKE BALL
[1] TOWN MAP
[2] BICYCLE
[3] POTION
[4] FULL HEAL
[5] REVIVE
</inventory>
</example_input>

<example_output>
{{
    "thoughts": "I need to use a Potion on my Pikachu. The potion is at index 3, so I will return 3.",
    "index": 3
}}
</example_output>

Reflect on the information provided to you and respond in the format given below. The relevant keys are:
- thoughts: Your very brief thoughts on which item to use based on the thought and inventory information provided to you in this prompt.
- index: The index of the item to use. This must be one of the indices listed above.
""".strip()
