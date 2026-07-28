"""LLM prompts for retrieve long term memory in the top-level agent graph."""

SELECT_LONG_TERM_MEMORY_PROMPT = """
Select the long-term memories that are relevant to the current situation. The available memory titles are:

<available_memory_titles>
{titles}
</available_memory_titles>

Here is the current state, including any long-term memories selected previously:

{state}

Titles use SCREAMING_SNAKE_CASE. Return only titles from the available list. Select no more than {max_memories} titles, choose the smallest useful set, and return an empty list if none of the memories are relevant.
""".strip()
