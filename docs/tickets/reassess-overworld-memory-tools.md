# Ticket: Reassess Overworld Memory Tools

## Outcome

Determine whether long-term-memory retrieval and the sprite and sign memories
provide enough decision quality to justify their prompt, tool-schema, and
persistence costs. Evaluate each mechanism independently, then retain,
simplify, consolidate, replace, or remove it based on evidence from actual play
rather than preserving it by default.

**Depends on:** completing the long-term-memory and goal-tool migration.

## Motivation

Long-term-memory retrieval loads only one document at a time and appends it to
the context for the current iteration. The agent must receive every available
title before it can use the tool, while rolling memory, goals, map state, and
ordinary tool results already provide substantial context. The resulting token
and attention cost may exceed the value of occasional manual document lookup.

Sprite and sign memories should receive the same scrutiny. Their descriptions
are persisted with explored-map entities and rendered back into map context,
with separate tools for maintaining them. They may preserve useful local
knowledge, but they may also repeat dialogue or observations already captured
elsewhere, become stale, or consume prompt space without changing decisions.

## Evaluation

- Measure how often representative playthroughs call the retrieval,
  `update_sprites`, and `update_signs` tools.
- Review whether retrieved documents and entity descriptions materially change
  later decisions or merely repeat information already present in rolling
  memory, dialogue history, goals, or current map state.
- Evaluate sprite and sign memories separately; their stability and value may
  differ, and they need not receive the same treatment.
- Measure the prompt cost of the complete long-term-memory title list, stored
  entity descriptions, and the associated tool schemas as the data grows.
- Review sprite and sign descriptions for usefulness, duplication, and
  staleness over representative playthroughs.
- Identify the appropriate owner and lifecycle for durable entity knowledge if
  it remains: map entities, long-term memory, another existing context source,
  or no persistent store.
- Identify what long-term-memory creation and update should mean if retrieval
  is removed.
- Compare removal with simpler alternatives, including deterministic context
  loading at meaningful boundaries and cheaper map annotations.

## Decision

Document the evidence and make a separate decision for long-term-memory
retrieval, sprite memory, and sign memory. For each mechanism:

- retain it with a clear demonstrated use case;
- simplify or consolidate it into a cheaper context policy; or
- remove it and its prompt preparation, tools, and persistence behavior when
  those no longer have a consumer.
