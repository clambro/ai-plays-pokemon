# Ticket: Simplify Long-Term Memory

## Outcome

Replace embedding-based retrieval with agent-guided lookup by memory title.
Show the agent the available titles, let it select the relevant ones, and load
those records through exact database queries.

This is a standalone memory task. It does not introduce Pydantic AI, change
mode orchestration, replace Gemini, or redesign rolling short-term memory.

## Retrieval

The existing memory title is the lookup key. Replace the generated semantic
query with a structured response containing a bounded list of titles:

1. Load the available long-term-memory titles.
2. Show those titles alongside the current game and agent context.
3. Ask the model which titles are relevant.
4. Validate the selection and retrieve those records by exact title.
5. Render the selected records through the existing long-term-memory prompt
   section.

The model decides what it wants to remember, while lookup remains simple and
deterministic. The current Junjo retrieval node can perform this selection
until the Pydantic Agents migration exposes the same behavior as a tool.

## Persistence

Keep the existing SQLite long-term-memory table and repository. Preserve each
record's:

- title;
- content;
- importance;
- creation iteration;
- update iteration; and
- last-accessed iteration.

Continue updating the access iteration when a selected memory is read. Existing
creation and update behavior should remain intact apart from no longer
generating or storing embeddings.

## Removal

Remove:

- the embedding column and embedding generation;
- the Gemini embedding client;
- vector serialization used only by long-term memory;
- cosine similarity and reranking;
- semantic-similarity and reranking settings; and
- NumPy if nothing else uses it.

Gemini remains the temporary generation provider for title selection and memory
maintenance until the separate Luna ticket.

## Completion

- The agent selects memories from the visible list of existing titles.
- Selected memories are loaded through exact title lookup.
- Existing long-term-memory records and iteration metadata continue to work.
- No embedding, vector, cosine-similarity, or semantic-ranking behavior
  remains.
- Title selection and exact lookup are covered by focused tests.
