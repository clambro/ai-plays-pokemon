# Ticket: Reassess Overworld Memory Tools

## Outcome

Remove unused agent-authored sprite and sign descriptions while retaining the
discovered entity records used to reconstruct explored maps.

Long-term memory and editable entity descriptions were removed as part of this
cleanup. Neither justified a second durable semantic-memory mechanism alongside
rolling memory.

## Motivation

Map-entity persistence has a real structural consumer. It records which
sprites, signs, and warps have been discovered, allowing the explored map to
reconstruct current coordinates, sprite labels, warp destinations, and entity
visibility from live emulator state.

The editable description layer had no effective producer. In representative
play, the agent discovered 18 sprites and 8 signs without writing a single
description. Dialogue already entered rolling memory, while the optional update
tools competed with gameplay actions and could not reliably attribute trainer
battles, scripted scenes, or moving sprites to a single entity.

## Evaluation

- Preserve discovered entity identities and their existing structural
  consumers.
- Remove the unused description field, description-update tools, and associated
  prompt text.
- Remove entity creation and update timestamps, which existed only to support
  editable descriptions and have no remaining consumer.
- Keep explored-map timestamps unchanged because terrain discovery is still an
  evolving persisted record.

## Decision

Long-term memory, its tools, prompt preparation, agent state, and persistence
code are removed. Rolling memory remains the durable chronological context.

Map-entity discovery remains. Agent-authored sprite and sign descriptions,
their tools, persistence fields, timestamps, and prompt guidance are removed.
If actual play later demonstrates a need for spatially indexed semantic memory,
it should be reintroduced with a concrete producer and retrieval lifecycle
rather than restoring unused manual annotation tools.
