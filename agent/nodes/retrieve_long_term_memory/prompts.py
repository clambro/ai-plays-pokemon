GET_RETRIEVAL_QUERY_PROMPT = """
It is your job to come up with a query string for the long-term memory retrieval service. Your query string will be matched semantically against pieces of long-term memory stored in the database, and whichever pieces are most relevant will be returned for use in the current agent context. Here is the relevant information, including the long term memory objects that were retrieved in the previous iteration:

{raw_memory}

{summary_memory}

{long_term_memory}

{player_info}

{goals}

Some useful things to include in your query string are:
- The map you are currently on
- Information about your goals
- What is going on in the game: Are you in a battle? Are you exploring? Are you talking to someone? Are you looking for something?

Your query string must be a single paragraph explaining the current state of the game and what information you need to retrieve from the long-term memory. Do not include any preamble or postamble in your response. Everything you write in your response will be used exactly as written to query the long-term memory.
""".strip()
