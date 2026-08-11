# Ticket: Reassess Overworld Memory Tools

## Outcome

Determine whether sprite and sign memories provide enough decision quality to
justify their prompt, tool-schema, and persistence costs. Evaluate each
mechanism independently, then retain, simplify, consolidate, replace, or remove
it based on evidence from actual play rather than preserving it by default.

Long-term memory was removed as the first part of this cleanup. The agent did
not use it enough to justify a second durable memory system alongside rolling
memory.

## Motivation

Sprite and sign memories should receive the same scrutiny. Their descriptions
are persisted with explored-map entities and rendered back into map context,
with separate tools for maintaining them. They may preserve useful local
knowledge, but they may also repeat dialogue or observations already captured
elsewhere, become stale, or consume prompt space without changing decisions.

## Evaluation

- Measure how often representative playthroughs call the `update_sprites` and
  `update_signs` tools.
- Review whether entity descriptions materially change later decisions or
  merely repeat information already present in rolling memory, dialogue
  history, goals, or current map state.
- Evaluate sprite and sign memories separately; their stability and value may
  differ, and they need not receive the same treatment.
- Measure the prompt cost of stored entity descriptions and the associated tool
  schemas as the data grows.
- Review sprite and sign descriptions for usefulness, duplication, and
  staleness over representative playthroughs.
- Identify the appropriate owner and lifecycle for durable entity knowledge if
  it remains: map entities, another existing context source, or no persistent
  store.
- Compare removal with simpler alternatives, including deterministic context
  loading at meaningful boundaries and cheaper map annotations.

## Decision

Long-term memory, its tools, prompt preparation, agent state, and persistence
code are removed. Rolling memory remains the durable chronological context.

Document the evidence and make a separate decision for sprite memory and sign
memory. For each mechanism:

- retain it with a clear demonstrated use case;
- simplify or consolidate it into a cheaper context policy; or
- remove it and its prompt preparation, tools, and persistence behavior when
  those no longer have a consumer.
