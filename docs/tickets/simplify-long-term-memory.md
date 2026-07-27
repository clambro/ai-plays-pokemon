# Ticket: Simplify Long-Term Memory

## Outcome

Replace the embedding-based retrieval system with a small bounded notebook
that is loaded in full and shown directly to the model.

Long-term memory should be predictable: every stored entry is visible, every
change is explicit, and no separate model call decides which memories the
agent is allowed to remember.

This is a standalone memory task. It does not introduce Pydantic AI, change
mode orchestration, remove Junjo, or redesign rolling short-term memory.

## Memory Model

Represent long-term memory as an ordered collection of concise named entries.
An entry needs only a stable title and content. Remove embeddings, importance
scores, creation and access iterations, similarity scores, and reranking
metadata.

Render every entry into the long-term-memory prompt section in a deterministic
order. The prompt should describe it as the complete notebook, not a retrieved
subset.

Keep the notebook intentionally small:

- configure a limit for each entry and for the notebook as a whole;
- reject writes that exceed those limits;
- require an existing entry to be replaced or removed when space is needed;
  and
- do not silently truncate, evict, summarize, or hide entries.

Finalize the limits using representative gameplay notes. They should allow
useful map, character, team, and strategy notes while keeping the entire
notebook cheap enough to include in normal prompts.

Use an internal dataclass for the notebook and entries. Keep validation models
at persistence and LLM boundaries.

## Operations and Persistence

Expose direct operations to:

- read the complete notebook;
- create a uniquely named entry;
- replace an existing entry;
- remove an entry; and
- persist a batch of changes atomically.

Replacement is the only update operation. Do not preserve append as a separate
concept: the caller can supply the complete revised entry, which makes the
result easy to inspect and keeps entries concise.

Keep the notebook in application state after startup instead of querying
storage during every prompt. Successful mutations update persistence and the
in-memory notebook together. A failed or invalid batch leaves both unchanged.

Simplify the existing long-term-memory table and repository around these
operations. V2 starts with an empty notebook, so no migration or import path is
required for the old embedding-backed records.

## Current Junjo Integration

Remove the retrieval branch from the root graph:

- delete the generated retrieval-query prompt and model call;
- delete embedding generation, cosine similarity, and reranking;
- delete the cached retrieved subset and retrieval cadence state; and
- render the complete notebook wherever long-term memory is currently used.

Until orchestration is redesigned separately, replace the concurrent create
and update nodes with one small periodic maintenance step. It sees the complete
notebook and may return a bounded batch of create, replace, or remove
operations, including an empty batch.

Validate the full batch against one notebook snapshot and commit it
atomically. Duplicate creates, updates or removals of missing titles, invalid
titles, and over-budget results reject the batch without partial changes.

The maintenance step is only the current workflow integration. The notebook,
mutation operations, persistence, and rendering must not depend on Junjo.

## Removal

Remove the obsolete:

- retrieval service and retrieval node;
- retrieval-query prompt;
- embedding service and stored embedding column;
- LTM-specific vector type if nothing else uses it;
- NumPy dependency if nothing else uses it;
- semantic-similarity, retrieval-count, reranking, and retrieval-cadence
  settings;
- create/update services that generate embeddings; and
- state fields that track a retrieved subset or retrieval timing.

## Completion

- Every stored long-term-memory entry appears in normal prompt context.
- The notebook enforces explicit entry and total-size limits without hidden
  information loss.
- Create, replace, and remove batches are validated and persisted atomically.
- The running Junjo application maintains the new notebook without a retrieval
  phase.
- No LTM embedding, generated-query, similarity, importance, recency, or
  reranking behavior remains.
- Persistence, rendering, limits, mutation failures, and the temporary
  maintenance integration are covered by tests.
